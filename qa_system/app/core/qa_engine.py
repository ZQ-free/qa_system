"""
app/core/qa_engine.py — 问答引擎总调度

职责：串联整个 RAG 流程，是接口层和各功能模块之间的唯一桥梁。
接口层只调用 QAEngine.process()，不直接接触任何子模块。

完整 RAG 流程：
  用户问题
    → [意图识别 + 数据查询] Graph Agent（内部调用 MySQL/Neo4j Tool）
    → [LLM润色 + 溯源标注] AnswerBuilder
    → 返回 AskResponse
"""

from app.core.answer_builder import AnswerBuilder
from app.retrieval.llm_generator import LLMGenerator


class QAEngine:
    """
    问答流程的总调度器。
    所有模块在这里被初始化和串联。
    """

    def __init__(self):
        self.llm = LLMGenerator()
        self.answer_builder = AnswerBuilder(llm_generator=self.llm)

    def create_graph_agent(self):
        """
        创建 Graph Agent 实例（LangGraph CompiledStateGraph）。
        供 session_manager 或测试代码调用。
        """
        from app.agents.graph_agent import create_graph_agent as _create
        return _create()

    async def process(self, question: str, session_id: str = None) -> dict:
        """
        处理一次用户提问，返回完整的响应。

        这是整个子系统对外的核心方法，接口层只调用这里。
        """

        agent = self.create_graph_agent()

        result = agent.invoke({"messages": [("user", question)]})

        messages = result.get("messages", [])
        ai_messages = [m for m in messages if hasattr(m, "type") and m.type == "ai"]

        graph_answer = ai_messages[-1].content if ai_messages else ""

        response = await self.answer_builder.build(
            question=question,
            intent="GRAPH_AGENT",
            entity="",
            kg_results=[{"text": graph_answer, "source": "graph_agent"}],
            intermediate_steps=messages,
        )

        return response