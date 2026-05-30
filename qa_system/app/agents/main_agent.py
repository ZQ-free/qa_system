"""
app/agents/main_agent.py — Main QA Agent（主问答 Agent）

职责：
1. 接收用户问题
2. 调用 Graph Agent 获取 RAG context
3. 将 RAG context 和问题一起发送给 LLM 生成最终回答
4. 流式输出给前端
5. 支持前端停止信号
"""

import json
import asyncio
from typing import Callable, Optional, Any
from openai import AsyncOpenAI
from config import settings
from app.agents.graph_agent import run_graph_agent


async def run_main_agent(
    question: str,
    history: list,
    token_callback: Callable[[str], None],
    done_callback: Callable[[Any], None],
    session_id: str = "",
    agent_step_callback: Optional[Callable[[str, str], None]] = None,
    stop_event: Optional[asyncio.Event] = None,
) -> None:
    import logging
    logging.info(f"[MainAgent] Processing: {question[:50]}...")
    logging.info(f"[MainAgent] === Starting Main Agent ===")
    logging.info(f"[MainAgent] Session: {session_id[:8] if session_id else 'none'}...")

    if stop_event is None:
        stop_event = asyncio.Event()

    async def on_tool_call(tool_name: str, tool_args: str):
        logging.info(f"[MainAgent] Tool called: {tool_name}")
        if agent_step_callback:
            await agent_step_callback("tool_call", f"正在调用 {tool_name}...")

    async def on_tool_result(tool_name: str, result: str):
        logging.info(f"[MainAgent] Tool result: {tool_name}, result_len: {len(result)}")
        if agent_step_callback:
            if "error" in result:
                await agent_step_callback("tool_result", f"{tool_name} 执行失败")
            else:
                try:
                    import json as json_mod
                    data = json_mod.loads(result)
                    if isinstance(data, list):
                        logging.info(f"[MainAgent] Tool returned {len(data)} items")
                        await agent_step_callback("tool_result", f"{tool_name} 返回 {len(data)} 条结果")
                    else:
                        await agent_step_callback("tool_result", f"{tool_name} 返回结果")
                except:
                    await agent_step_callback("tool_result", f"{tool_name} 返回结果")

    logging.info(f"[MainAgent] Calling Graph Agent for RAG context...")
    graph_result = await run_graph_agent(
        question=question,
        session_id=session_id,
        stop_event=stop_event,
        on_tool_call=on_tool_call,
        on_tool_result=on_tool_result,
    )

    logging.info(f"[MainAgent] Graph Agent returned rag_context: {len(graph_result.get('rag_context', ''))} chars")

    if stop_event.is_set():
        logging.info("[MainAgent] Stopped after graph agent")
        await done_callback(None)
        return

    rag_context = graph_result.get("rag_context", "")

    if not rag_context:
        logging.warning(f"[MainAgent] No rag_context from graph agent, proceeding without database info")
        rag_context = "未从数据库查询到相关信息。"

    client = AsyncOpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        timeout=settings.LLM_TIMEOUT,
    )

    system_prompt = """你是一个专业的海外藏中国文物知识问答助手。

根据以下 RAG context（数据库查询结果）回答用户问题。

要求：
- 直接、简洁地回答问题
- 如果 RAG context 有相关信息，基于它回答
- 如果没有相关信息，直接告知用户
- 不要重复用户的问题
- 如有 detail_url 溯源链接，在回答中适当提及
"""

    user_content = f"""用户问题：{question}

数据库查询结果（RAG Context）：
{rag_context}

请根据以上信息回答用户问题："""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]

    logging.info(f"[MainAgent] Calling LLM for final answer...")
    logging.info(f"[MainAgent] RAG context length: {len(rag_context)} chars")

    try:
        stream = await client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=messages,
            stream=True,
            temperature=0.1,
        )
        logging.info(f"[MainAgent] LLM stream started...")

        full_response = ""
        async for chunk in stream:
            if stop_event.is_set():
                logging.info("[MainAgent] Stopped during streaming")
                if full_response:
                    await done_callback({
                        "content": full_response,
                        "intent_label": graph_result.get("intent_label", "UNKNOWN")
                    })
                else:
                    await done_callback(None)
                return

            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            if delta is None:
                continue

            if delta.content:
                full_response += delta.content
                await token_callback(delta.content)

        logging.info(f"[MainAgent] Streaming finished, total: {len(full_response)} chars")
        await done_callback({
            "content": full_response,
            "intent_label": graph_result.get("intent_label", "UNKNOWN")
        })

    except Exception as e:
        logging.error(f"[MainAgent] LLM call failed: {e}")
        await done_callback({
            "content": f"生成回答时出错: {str(e)}",
            "intent_label": "ERROR"
        })