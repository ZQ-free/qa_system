"""
app/retrieval/mock_retriever.py — Mock 数据检索器
【负责人：成员C】

职责：在子系统1（知识图谱）尚未完成接入的时候，提供假数据让整个流程可以运行。（测试中使用，优先级没有很强）

使用方式：config.py 中设置 MOCK_MODE=True，QAEngine 会自动使用此模块。
切换到真实数据：MOCK_MODE=False，自动切换到 graph_retriever.py。

【成员C的工作】：注意要对齐目前子系统1的数据字段（用ai生成一下数据就可以了）
  补充各意图的 Mock 数据，每个意图至少 3 条，覆盖：
  - 正常有数据的情况（返回列表）
  - 没有找到数据的情况（返回空列表，用于测试 not_found 逻辑）
  
Mock 数据的字段名要和 CYPHER_TEMPLATES 的 RETURN 子句保持一致，
这样切换到真实图谱时，answer_builder 的代码不需要任何改动。
"""

from app.core.intent_types import Intent


# ══════════════════════════════════════════════════════════════════════════════
# Mock 数据库
# 字段名必须和 query_builder.py 中 Cypher 的 RETURN 字段名完全一致
# ══════════════════════════════════════════════════════════════════════════════

MOCK_DATA = {

    Intent.ARTIFACT_LOCATION: [
        {
            "artifact_name": "青花云龙纹罐",
            "object_id": "CMA_1234",
            "detail_url": "https://www.clevelandart.org/art/1234",
            "museum_name": "Cleveland Museum of Art",
            "city": "Cleveland",
            "country": "USA",
        },
        {
            "artifact_name": "青花缠枝莲纹碗",
            "object_id": "MET_5678",
            "detail_url": "https://www.metmuseum.org/art/collection/5678",
            "museum_name": "The Metropolitan Museum of Art",
            "city": "New York",
            "country": "USA",
        },
    ],

    Intent.ARTIFACT_PERIOD: [
        {
            "artifact_name": "青花云龙纹罐",
            "object_id": "CMA_1234",
            "detail_url": "https://www.clevelandart.org/art/1234",
            "dynasty_name": "元朝",
            "start_year": "1271",
            "end_year": "1368",
        },
    ],

    Intent.ARTIFACT_MATERIAL: [
        {
            "artifact_name": "青花云龙纹罐",
            "object_id": "CMA_1234",
            "detail_url": "https://www.clevelandart.org/art/1234",
            "material": "Porcelain with cobalt blue underglaze",
            "museum_name": "Cleveland Museum of Art",
        },
    ],

    Intent.ARTIFACT_TYPE: [
        {
            "artifact_name": "青花云龙纹罐",
            "object_id": "CMA_1234",
            "detail_url": "https://www.clevelandart.org/art/1234",
            "artifact_type": "Ceramics",
            "museum_name": "Cleveland Museum of Art",
        },
    ],

    Intent.ARTIFACT_INTRODUCTION: [
        {
            "artifact_name": "青花云龙纹罐",
            "object_id": "CMA_1234",
            "detail_url": "https://www.clevelandart.org/art/1234",
            "description": (
                "This Yuan dynasty jar features a dynamic dragon amid clouds, "
                "rendered in cobalt blue on white porcelain. The bold brushwork "
                "and lively composition exemplify the finest Yuan blue-and-white ware."
            ),
            "artifact_type": "Ceramics",
            "material": "Porcelain with cobalt blue underglaze",
            "museum_name": "Cleveland Museum of Art",
            "dynasty_name": "元朝",
        },
    ],

    Intent.ARTIFACT_AUTHOR: [
        {
            "artifact_name": "溪山清远图",
            "object_id": "MET_9012",
            "detail_url": "https://www.metmuseum.org/art/collection/9012",
            "artist_name": "夏圭",
            "museum_name": "The Metropolitan Museum of Art",
        },
    ],

    Intent.AUTHOR_BIOGRAPHY: [
        {
            "artist_name": "夏圭",
            "biography": (
                "夏圭，字禹玉，钱塘（今浙江杭州）人，南宋著名画家。"
                "与马远齐名，并称"'马夏'"，是南宋院体画的代表人物之一。"
                "擅长山水画，笔墨简练，意境深远，对后世影响深远。"
            ),
            "birth_year": "约1195",
            "death_year": "约1224",
        },
    ],

    Intent.AUTHOR_OTHER_WORKS: [
        {
            "artifact_name": "溪山清远图",
            "object_id": "MET_9012",
            "detail_url": "https://www.metmuseum.org/art/collection/9012",
            "artifact_type": "Painting",
            "museum_name": "The Metropolitan Museum of Art",
        },
        {
            "artifact_name": "雪堂客话图",
            "object_id": "MFA_3456",
            "detail_url": "https://www.mfa.org/collections/3456",
            "artifact_type": "Painting",
            "museum_name": "Museum of Fine Arts, Boston",
        },
    ],

    Intent.DYNASTY_ARTIFACTS: [
        {
            "artifact_name": "青花云龙纹罐",
            "object_id": "CMA_1234",
            "detail_url": "https://www.clevelandart.org/art/1234",
            "artifact_type": "Ceramics",
            "museum_name": "Cleveland Museum of Art",
            "dynasty_name": "元朝",
        },
        {
            "artifact_name": "青花缠枝牡丹纹梅瓶",
            "object_id": "MET_2345",
            "detail_url": "https://www.metmuseum.org/art/collection/2345",
            "artifact_type": "Ceramics",
            "museum_name": "The Metropolitan Museum of Art",
            "dynasty_name": "元朝",
        },
    ],

    Intent.ARTIFACT_DIMENSIONS: [
        {
            "artifact_name": "青花云龙纹罐",
            "object_id": "CMA_1234",
            "detail_url": "https://www.clevelandart.org/art/1234",
            "dimensions": "H. 33.7 cm (13 1/4 in.)",
            "museum_name": "Cleveland Museum of Art",
        },
    ],
}


class MockRetriever:
    """
    Mock 检索器，接口与 GraphRetriever 完全相同（同名方法，同返回格式）。
    QAEngine 通过 MOCK_MODE 自动选择使用哪个，切换时无需修改任何其他代码。
    """

    async def retrieve(self, cypher: str, params: dict) -> list:
        """
        根据查询参数，从 Mock 数据库中返回匹配的数据。
        
        当前实现：根据意图类型返回对应的 Mock 数据（忽略实体名过滤）。
        
        【成员C可优化】：让 Mock 数据支持按实体名过滤，更真实地模拟图谱行为。
        比如：查询"青花瓷"时只返回名称包含"青花"的记录。
        """
        # 从 Cypher 语句中推断意图（通过查询语句的特征）
        # 这是简化实现，成员C可以改为通过额外参数传递意图
        intent = self._infer_intent_from_cypher(cypher)
        entity = params.get("entity", "")

        mock_list = MOCK_DATA.get(intent, [])

        # 简单过滤：如果实体名不为空，只返回名称中包含实体名的记录
        if entity and mock_list:
            filtered = [
                r for r in mock_list
                if entity.lower() in r.get("artifact_name", "").lower()
                or entity.lower() in r.get("artist_name", "").lower()
                or entity.lower() in r.get("dynasty_name", "").lower()
            ]
            # 如果过滤后为空（实体名不匹配），返回空列表，触发 not_found 逻辑
            return filtered if filtered else []

        return mock_list

    def _infer_intent_from_cypher(self, cypher: str) -> str:
        """根据 Cypher 语句中的关键特征推断意图类型"""
        cypher_lower = cypher.lower()
        if "biography" in cypher_lower or "bio" in cypher_lower:
            return Intent.AUTHOR_BIOGRAPHY
        if "birth_year" in cypher_lower and "artist" in cypher_lower:
            return Intent.AUTHOR_BIOGRAPHY
        if "dynasty_name" in cypher_lower and "artifact_name" in cypher_lower and "museum_name" not in cypher_lower:
            return Intent.ARTIFACT_PERIOD
        if "artist_name" in cypher_lower and "museum_name" in cypher_lower and "artifact_name" in cypher_lower:
            # AUTHOR_OTHER_WORKS 和 ARTIFACT_AUTHOR 都有这些字段，通过 rel 方向区分
            if "created_by" in cypher_lower and "<-" in cypher_lower:
                return Intent.AUTHOR_OTHER_WORKS
            return Intent.ARTIFACT_AUTHOR
        if "biography" in cypher_lower:
            return Intent.AUTHOR_BIOGRAPHY
        if "dimensions" in cypher_lower:
            return Intent.ARTIFACT_DIMENSIONS
        if "description" in cypher_lower:
            return Intent.ARTIFACT_INTRODUCTION
        if "artifact_type" in cypher_lower and "dynasty_name" in cypher_lower:
            return Intent.DYNASTY_ARTIFACTS
        if "artifact_type" in cypher_lower:
            return Intent.ARTIFACT_TYPE
        if "material" in cypher_lower:
            return Intent.ARTIFACT_MATERIAL
        if "dynasty_name" in cypher_lower:
            return Intent.ARTIFACT_PERIOD
        # 默认返回收藏地
        return Intent.ARTIFACT_LOCATION
