"""
app/core/qa_engine.py — 问答引擎总调度

职责：串联整个 RAG 流程，是接口层和各功能模块之间的唯一桥梁。
接口层只调用 QAEngine.process()，不直接接触任何子模块。

完整 RAG 流程：
  用户问题
    → [意图识别] IntentParser.parse()         (成员A)
    → [查询构建] QueryBuilder.build()          (成员B)
    → [图谱检索] GraphRetriever.retrieve()     (成员D)
    → [答案组装] AnswerBuilder.build()         (组长)
       └── [LLM润色] LLMGenerator.generate()  (成员C，在 AnswerBuilder 内调用)
    → 返回 AskResponse
"""

from config import settings
from app.core.intent_parser import IntentParser
from app.core.query_builder import QueryBuilder
from app.core.answer_builder import AnswerBuilder
from app.core.intent_types import Intent

# 根据 MOCK_MODE 选择使用真实检索器还是 Mock 检索器
if settings.MOCK_MODE:
    from app.retrieval.mock_retriever import MockRetriever as GraphRetriever
else:
    from app.retrieval.graph_retriever import GraphRetriever

from app.retrieval.llm_generator import LLMGenerator
from app.models.schemas import AskResponse


class QAEngine:
    """
    问答流程的总调度器。
    所有模块在这里被初始化和串联。
    """

    def __init__(self):
        # 按依赖顺序初始化各模块
        self.llm = LLMGenerator()                          # 成员C：大模型客户端
        self.intent_parser = IntentParser(llm_client=self.llm)  # 成员A：意图识别
        self.query_builder = QueryBuilder()                     # 成员B：查询构建
        self.graph_retriever = GraphRetriever()                 # 成员D：图谱检索
        self.answer_builder = AnswerBuilder(llm_generator=self.llm)  # 组长：答案组装

    async def process(self, question: str, session_id: str = None) -> AskResponse:
        """
        处理一次用户提问，返回完整的 AskResponse。
        
        这是整个子系统对外的核心方法，接口层只调用这里。
        """

        # ── Step 1: 意图识别 + 实体抽取 ───────────────────────
        # 输入："青花瓷现藏于哪里？"
        # 输出：{"intent": "artifact_location", "entity": "青花瓷"}
        parse_result = await self.intent_parser.parse(question)
        intent = parse_result.get("intent", Intent.UNKNOWN)
        entity = parse_result.get("entity", "")

        # ── Step 2: 构建 Cypher 查询 ───────────────────────────
        # 如果意图是 UNKNOWN，query_config 为 None，直接跳到答案组装返回"暂无数据"
        query_config = self.query_builder.build(intent, entity)

        # ── Step 3: 知识图谱检索 ────────────────────────────────
        kg_results = []
        if query_config:
            kg_results = await self.graph_retriever.retrieve(
                cypher=query_config["cypher"],
                params=query_config["params"],
            )

        # ── Step 4: 组装答案（含LLM润色 + 溯源标注）─────────────
        response = await self.answer_builder.build(
            question=question,
            intent=intent,
            entity=entity,
            kg_results=kg_results,
        )

        return response
