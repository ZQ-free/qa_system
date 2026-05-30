"""
Main QA Agent — 主问答 Agent

双 Agent 架构中的"主问答 Agent"。

职责：
1. 管理会话历史（存储到数据库 ai_history）
2. 向 Graph Agent 注入历史上下文（支持多轮对话）
3. 接收 Graph Agent 的结构化结论（finalize_answer）
4. 将结论润色为流畅自然语言，返回给用户
5. 将 user + assistant 消息写入数据库

与 Graph Agent 的分工：
  Graph Agent = 意图识别 + 数据查询 + 结构化输出（answer_text + sources）
  Main QA Agent = 会话历史管理 + 上下文注入 + 润色生成 + 存储

设计原则：
- Main QA Agent 持有数据库级别的会话历史（ai_history）
- Graph Agent 持有内存级别的对话上下文（用于理解多轮意图）
- 两者的历史独立维护，互不干扰
"""

import json
from typing import Optional
from langchain_core.messages import HumanMessage
from config import settings
from app.retrieval.llm_generator import create_llm


class MainQAAgent:
    def __init__(self):
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            self._llm = create_llm(temperature=0.1)
        return self._llm

    def _build_messages(self, chat_history: list[dict], current_question: str) -> list:
        """
        将数据库历史转换为 LangChain 消息格式，供 Graph Agent 理解上下文。
        同时注入一个 HumanMessage 使 Graph Agent 知道这是多轮对话。
        """
        messages = []

        if chat_history:
            context_lines = []
            for record in chat_history[-10:]:
                role = record.get("role", "")
                content = record.get("content", "")
                if role == "user":
                    context_lines.append(f"用户：{content}")
                elif role == "assistant":
                    context_lines.append(f"助手：{content}")

            if context_lines:
                messages.append(HumanMessage(
                    content="【对话历史摘要】\n" + "\n".join(context_lines)
                    + "\n\n以上是之前的对话，当前问题请结合历史上下文理解。"
                ))

        messages.append(HumanMessage(content=current_question))
        return messages

    async def process(
        self,
        question: str,
        session_id: str,
        chat_history: list[dict],
    ) -> dict:
        """
        处理用户提问。

        流程：
          1. 构建注入历史上下文的 LangChain 消息
          2. 调用 Graph Agent（内部完成 Tool 查询 + finalize_answer）
          3. 从 Graph Agent 的 tool_calls 中解析 finalize_answer 结果
          4. 将 user + assistant 消息写入 ai_history
        """
        from app.agents.graph_agent import create_graph_agent, MYSQL_TOOLS, NEO4J_TOOLS
        from app.db.mysql_client import get_pool

        langchain_messages = self._build_messages(chat_history, question)

        agent = create_graph_agent()

        result = agent.invoke({"messages": langchain_messages})
        messages = result.get("messages", [])

        finalized_result = self._extract_finalized_result(messages)

        if not finalized_result:
            finalized_result = {
                "answer_text": "抱歉，查询过程中未获得有效结论，请稍后重试。",
                "sources": [],
                "intent_label": "UNKNOWN",
            }

        answer_text = finalized_result["answer_text"]
        sources = finalized_result["sources"]
        intent_label = finalized_result["intent_label"]

        pool = await get_pool()
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """INSERT INTO ai_history
                           (session_id, role, content, intent, streaming_done)
                           VALUES (%s, 'user', %s, %s, TRUE)""",
                        (session_id, question, intent_label),
                    )
                    await cur.execute("SELECT LAST_INSERT_ID()")
                    user_row = await cur.fetchone()
                    user_msg_id = user_row[0] if user_row else 0

                    await cur.execute(
                        """INSERT INTO ai_history
                           (session_id, role, content, intent, streaming_done)
                           VALUES (%s, 'assistant', %s, %s, TRUE)""",
                        (session_id, answer_text, intent_label),
                    )
                    await cur.execute("SELECT LAST_INSERT_ID()")
                    assistant_row = await cur.fetchone()
                    assistant_msg_id = assistant_row[0] if assistant_row else 0

                    await conn.commit()
        finally:
            pass

        return {
            "answer_text": answer_text,
            "sources": sources,
            "intent_label": intent_label,
            "user_msg_id": user_msg_id,
            "assistant_msg_id": assistant_msg_id,
        }

    def _extract_finalized_result(self, messages: list) -> Optional[dict]:
        """
        从 Graph Agent 的 messages 中解析 finalize_answer 工具调用的结果。
        """
        for msg in reversed(messages):
            if not hasattr(msg, "tool_calls") or not msg.tool_calls:
                continue
            for tc in msg.tool_calls:
                if tc.get("name") == "finalize_answer":
                    args = tc.get("args", {})
                    answer_text = args.get("answer_text", "")
                    sources_raw = args.get("sources", "[]")
                    intent_label = args.get("intent_label", "UNKNOWN")
                    try:
                        sources = json.loads(sources_raw) if isinstance(sources_raw, str) else sources_raw
                    except (json.JSONDecodeError, TypeError):
                        sources = []
                    if answer_text:
                        return {
                            "answer_text": answer_text,
                            "sources": sources,
                            "intent_label": intent_label,
                        }

        for msg in messages:
            if hasattr(msg, "type") and msg.type == "ai":
                content = msg.content or ""
                if "FINALIZED" in content:
                    return {
                        "answer_text": content.replace("FINALIZED", "").strip() or "查询完成",
                        "sources": [],
                        "intent_label": "UNKNOWN",
                    }

        return None

    async def generate_polished_answer(
        self,
        question: str,
        answer_text: str,
        sources: list,
    ) -> str:
        """
        将 Graph Agent 的结构化结论润色为流畅的自然语言。
        """
        if not answer_text or answer_text in ("数据库中暂无相关数据", "抱歉，查询过程中未获得有效结论，请稍后重试。"):
            return answer_text

        llm = self._get_llm()
        polished = await llm.ainvoke([
            HumanMessage(
                content=f"""你是一个专业的文物知识问答助手。请将以下查询结果润色为流畅自然的回答，直接回复用户。

用户问题：{question}

查询结果：
{answer_text}

溯源信息：
{json.dumps(sources, ensure_ascii=False, indent=2)}

要求：
- 直接回答问题，不说"根据查询结果"等过渡语
- 如有溯源链接，在回答末尾附上（格式：来源：博物馆名 - 链接）
- 不添加查询结果中没有的信息
"""
            )
        ])
        return polished.content if hasattr(polished, "content") else str(polished)


_main_qa_agent: Optional[MainQAAgent] = None


def get_main_qa_agent() -> MainQAAgent:
    global _main_qa_agent
    if _main_qa_agent is None:
        _main_qa_agent = MainQAAgent()
    return _main_qa_agent