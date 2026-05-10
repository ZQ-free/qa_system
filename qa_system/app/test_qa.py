"""
tests/test_qa.py — 单元测试
在 Mock 模式下，无需任何数据库或 LLM，可随时运行验证整体流程。

运行方式: pytest tests/test_qa.py -v
"""

import pytest
import asyncio
from app.core.intent_parser import IntentParser
from app.core.query_builder import QueryBuilder
from app.core.intent_types import Intent
from app.retrieval.mock_retriever import MockRetriever


# ── 意图识别测试（成员A负责补充）─────────────────────────────────────────

class TestIntentParser:
    """测试规则版意图识别（不依赖LLM）"""

    def setup_method(self):
        # 不传 llm_client，使用规则版
        self.parser = IntentParser(llm_client=None)

    @pytest.mark.asyncio
    async def test_artifact_location(self):
        result = await self.parser.parse("青花瓷现在藏在哪个博物馆？")
        assert result["intent"] == Intent.ARTIFACT_LOCATION

    @pytest.mark.asyncio
    async def test_artifact_period(self):
        result = await self.parser.parse("这件文物是什么朝代的？")
        assert result["intent"] == Intent.ARTIFACT_PERIOD

    @pytest.mark.asyncio
    async def test_artifact_material(self):
        result = await self.parser.parse("青花罐是什么材质的？")
        assert result["intent"] == Intent.ARTIFACT_MATERIAL

    @pytest.mark.asyncio
    async def test_author_biography(self):
        result = await self.parser.parse("夏圭的生平经历是怎样的？")
        assert result["intent"] == Intent.AUTHOR_BIOGRAPHY

    @pytest.mark.asyncio
    async def test_unknown_intent(self):
        result = await self.parser.parse("今天天气怎么样？")
        assert result["intent"] == Intent.UNKNOWN


# ── 查询构建测试（成员B负责补充）────────────────────────────────────────

class TestQueryBuilder:
    """测试 Cypher 模板是否正确生成"""

    def setup_method(self):
        self.builder = QueryBuilder()

    def test_known_intent_returns_query(self):
        result = self.builder.build(Intent.ARTIFACT_LOCATION, "青花瓷")
        assert result is not None
        assert "cypher" in result
        assert "MATCH" in result["cypher"]
        assert result["params"]["entity"] == "青花瓷"

    def test_unknown_intent_returns_none(self):
        result = self.builder.build(Intent.UNKNOWN, "")
        assert result is None

    def test_all_intents_have_template(self):
        """确保10类意图都有对应的 Cypher 模板"""
        for intent in Intent.all_known():
            result = self.builder.build(intent, "test")
            assert result is not None, f"意图 {intent} 缺少 Cypher 模板"


# ── Mock 检索器测试（成员C负责补充）────────────────────────────────────

class TestMockRetriever:
    """测试 Mock 数据是否能正常返回"""

    def setup_method(self):
        self.retriever = MockRetriever()
        self.builder = QueryBuilder()

    @pytest.mark.asyncio
    async def test_returns_list(self):
        query = self.builder.build(Intent.ARTIFACT_LOCATION, "青花")
        result = await self.retriever.retrieve(query["cypher"], query["params"])
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_not_found_returns_empty(self):
        """实体名不匹配时应该返回空列表，触发 not_found 逻辑"""
        query = self.builder.build(Intent.ARTIFACT_LOCATION, "这件文物不存在xyz123")
        result = await self.retriever.retrieve(query["cypher"], query["params"])
        assert result == []

    @pytest.mark.asyncio
    async def test_result_has_required_fields(self):
        """检查返回的字段名与 AnswerBuilder 期望的字段一致"""
        query = self.builder.build(Intent.ARTIFACT_LOCATION, "青花")
        results = await self.retriever.retrieve(query["cypher"], query["params"])
        if results:
            required_fields = ["artifact_name", "object_id", "detail_url", "museum_name"]
            for field in required_fields:
                assert field in results[0], f"Mock 数据缺少字段: {field}"
