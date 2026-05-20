"""
app/retrieval/mock_retriever.py — Mock 数据检索器
【负责人：成员C】

职责：在子系统1（知识图谱）尚未完成接入的时候，提供假数据让整个流程可以运行。
""""""
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
# Mock 数据库（每个意图至少3条数据）
# ══════════════════════════════════════════════════════════════════════════════

MOCK_DATA = {

    # ==================== 1. 文物收藏地 ====================
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
        {
            "artifact_name": "青铜爵",
            "object_id": "SHM_001",
            "detail_url": "https://www.shanghaimuseum.net/art/001",
            "museum_name": "上海博物馆",
            "city": "上海",
            "country": "China",
        },
    ],

    # ==================== 2. 文物年代 ====================
    Intent.ARTIFACT_PERIOD: [
        {
            "artifact_name": "青花云龙纹罐",
            "object_id": "CMA_1234",
            "detail_url": "https://www.clevelandart.org/art/1234",
            "dynasty_name": "元朝",
            "start_year": "1271",
            "end_year": "1368",
        },
        {
            "artifact_name": "溪山清远图",
            "object_id": "MET_9012",
            "detail_url": "https://www.metmuseum.org/art/collection/9012",
            "dynasty_name": "南宋",
            "start_year": "1127",
            "end_year": "1279",
        },
        {
            "artifact_name": "玉琮",
            "object_id": "ZJM_002",
            "detail_url": "https://www.zjmuseum.com/art/002",
            "dynasty_name": "良渚文化",
            "start_year": "约3300",
            "end_year": "约2300",
        },
    ],

    # ==================== 3. 文物材质 ====================
    Intent.ARTIFACT_MATERIAL: [
        {
            "artifact_name": "青花云龙纹罐",
            "object_id": "CMA_1234",
            "detail_url": "https://www.clevelandart.org/art/1234",
            "material": "青花瓷",
            "museum_name": "Cleveland Museum of Art",
        },
        {
            "artifact_name": "青铜爵",
            "object_id": "SHM_001",
            "detail_url": "https://www.shanghaimuseum.net/art/001",
            "material": "青铜",
            "museum_name": "上海博物馆",
        },
        {
            "artifact_name": "玉琮",
            "object_id": "ZJM_002",
            "detail_url": "https://www.zjmuseum.com/art/002",
            "material": "玉石",
            "museum_name": "浙江省博物馆",
        },
    ],

    # ==================== 4. 文物类型 ====================
    Intent.ARTIFACT_TYPE: [
        {
            "artifact_name": "青花云龙纹罐",
            "object_id": "CMA_1234",
            "detail_url": "https://www.clevelandart.org/art/1234",
            "artifact_type": "瓷器",
            "museum_name": "Cleveland Museum of Art",
        },
        {
            "artifact_name": "青铜爵",
            "object_id": "SHM_001",
            "detail_url": "https://www.shanghaimuseum.net/art/001",
            "artifact_type": "酒器",
            "museum_name": "上海博物馆",
        },
        {
            "artifact_name": "溪山清远图",
            "object_id": "MET_9012",
            "detail_url": "https://www.metmuseum.org/art/collection/9012",
            "artifact_type": "绘画",
            "museum_name": "The Metropolitan Museum of Art",
        },
    ],

    # ==================== 5. 文物介绍 ====================
    Intent.ARTIFACT_INTRODUCTION: [
        {
            "artifact_name": "青花云龙纹罐",
            "object_id": "CMA_1234",
            "detail_url": "https://www.clevelandart.org/art/1234",
            "description": "元代青花瓷代表作，绘有云龙纹，笔触豪放，青花发色浓郁。",
            "artifact_type": "瓷器",
            "material": "青花瓷",
            "museum_name": "Cleveland Museum of Art",
            "dynasty_name": "元朝",
        },
        {
            "artifact_name": "青铜爵",
            "object_id": "SHM_001",
            "detail_url": "https://www.shanghaimuseum.net/art/001",
            "description": "商代青铜酒器，造型古朴，纹饰精美，是研究商代礼制的重要实物。",
            "artifact_type": "酒器",
            "material": "青铜",
            "museum_name": "上海博物馆",
            "dynasty_name": "商代",
        },
        {
            "artifact_name": "玉琮",
            "object_id": "ZJM_002",
            "detail_url": "https://www.zjmuseum.com/art/002",
            "description": "良渚文化玉器，内圆外方，是古代祭祀用的礼器。",
            "artifact_type": "玉器",
            "material": "玉石",
            "museum_name": "浙江省博物馆",
            "dynasty_name": "良渚文化",
        },
    ],

    # ==================== 6. 文物作者 ====================
    Intent.ARTIFACT_AUTHOR: [
        {
            "artifact_name": "溪山清远图",
            "object_id": "MET_9012",
            "detail_url": "https://www.metmuseum.org/art/collection/9012",
            "artist_name": "夏圭",
            "museum_name": "The Metropolitan Museum of Art",
        },
        {
            "artifact_name": "富春山居图",
            "object_id": "ZJM_003",
            "detail_url": "https://www.zjmuseum.com/art/003",
            "artist_name": "黄公望",
            "museum_name": "浙江省博物馆",
        },
        {
            "artifact_name": "洛神赋图",
            "object_id": "GWM_004",
            "detail_url": "https://www.gugongmuseum.com/art/004",
            "artist_name": "顾恺之",
            "museum_name": "故宫博物院",
        },
    ],

    # ==================== 7. 作者生平 ====================
    Intent.AUTHOR_BIOGRAPHY: [
        {
            "artist_name": "夏圭",
            "biography": "夏圭，字禹玉，钱塘（今浙江杭州）人，南宋著名画家。与马远齐名，并称'马夏'，是南宋院体画的代表人物之一。",
            "birth_year": "约1195",
            "death_year": "约1224",
        },
        {
            "artist_name": "黄公望",
            "biography": "黄公望，字子久，号大痴，元代著名画家。擅画山水，代表作《富春山居图》。",
            "birth_year": "1269",
            "death_year": "1354",
        },
        {
            "artist_name": "顾恺之",
            "biography": "顾恺之，字长康，东晋著名画家、绘画理论家。代表作《洛神赋图》。",
            "birth_year": "约344",
            "death_year": "约406",
        },
    ],

    # ==================== 8. 同作者其他作品 ====================
    Intent.AUTHOR_OTHER_WORKS: [
        {
            "artifact_name": "溪山清远图",
            "object_id": "MET_9012",
            "detail_url": "https://www.metmuseum.org/art/collection/9012",
            "artifact_type": "绘画",
            "museum_name": "The Metropolitan Museum of Art",
        },
        {
            "artifact_name": "雪堂客话图",
            "object_id": "MFA_3456",
            "detail_url": "https://www.mfa.org/collections/3456",
            "artifact_type": "绘画",
            "museum_name": "Museum of Fine Arts, Boston",
        },
        {
            "artifact_name": "山水四景图",
            "object_id": "GWM_005",
            "detail_url": "https://www.gugongmuseum.com/art/005",
            "artifact_type": "绘画",
            "museum_name": "故宫博物院",
        },
    ],

    # ==================== 9. 同朝代文物 ====================
    Intent.DYNASTY_ARTIFACTS: [
        {
            "artifact_name": "青花云龙纹罐",
            "object_id": "CMA_1234",
            "detail_url": "https://www.clevelandart.org/art/1234",
            "artifact_type": "瓷器",
            "museum_name": "Cleveland Museum of Art",
            "dynasty_name": "元朝",
        },
        {
            "artifact_name": "青花缠枝牡丹纹梅瓶",
            "object_id": "MET_2345",
            "detail_url": "https://www.metmuseum.org/art/collection/2345",
            "artifact_type": "瓷器",
            "museum_name": "The Metropolitan Museum of Art",
            "dynasty_name": "元朝",
        },
        {
            "artifact_name": "元青花人物故事罐",
            "object_id": "HBM_006",
            "detail_url": "https://www.hbmuseum.com/art/006",
            "artifact_type": "瓷器",
            "museum_name": "湖北省博物馆",
            "dynasty_name": "元朝",
        },
    ],

    # ==================== 10. 文物尺寸 ====================
    Intent.ARTIFACT_DIMENSIONS: [
        {
            "artifact_name": "青花云龙纹罐",
            "object_id": "CMA_1234",
            "detail_url": "https://www.clevelandart.org/art/1234",
            "dimensions": "高33.7厘米，口径15.2厘米",
            "museum_name": "Cleveland Museum of Art",
        },
        {
            "artifact_name": "青铜爵",
            "object_id": "SHM_001",
            "detail_url": "https://www.shanghaimuseum.net/art/001",
            "dimensions": "高20.5厘米，长16.8厘米",
            "museum_name": "上海博物馆",
        },
        {
            "artifact_name": "玉琮",
            "object_id": "ZJM_002",
            "detail_url": "https://www.zjmuseum.com/art/002",
            "dimensions": "高8.9厘米，边长7.2厘米",
            "museum_name": "浙江省博物馆",
        },
    ],
}


class MockRetriever:
    """
    Mock 检索器，接口与 GraphRetriever 完全相同。
    QAEngine 通过 MOCK_MODE 自动选择使用哪个。
    """

    async def retrieve(self, cypher: str, params: dict) -> list:
        """
        根据查询参数，从 Mock 数据库中返回匹配的数据。
        
        支持按实体名过滤：
        - 如果实体名不为空，只返回名称中包含实体名的记录
        - 如果过滤后为空，返回空列表（触发 not_found 逻辑）
        """
        # 1. 从 Cypher 语句推断意图
        intent = self._infer_intent_from_cypher(cypher)
        
        # 2. 获取该意图的 Mock 数据
        entity = params.get("entity", "")
        mock_list = MOCK_DATA.get(intent, [])

        # 3. 按实体名过滤（模拟真实图谱查询）
        if entity and mock_list:
            filtered = []
            for r in mock_list:
                # 检查文物名、艺术家名、朝代名是否包含实体关键词
                if entity.lower() in r.get("artifact_name", "").lower():
                    filtered.append(r)
                elif entity.lower() in r.get("artist_name", "").lower():
                    filtered.append(r)
                elif entity.lower() in r.get("dynasty_name", "").lower():
                    filtered.append(r)
            
            # 如果过滤后为空，返回空列表（测试 not_found 逻辑）
            return filtered if filtered else []

        return mock_list

    def _infer_intent_from_cypher(self, cypher: str) -> str:
        """根据 Cypher 语句特征推断意图类型"""
        c = cypher.lower()
        
        if "biography" in c:
            return Intent.AUTHOR_BIOGRAPHY
        if "dimensions" in c:
            return Intent.ARTIFACT_DIMENSIONS
        if "description" in c:
            return Intent.ARTIFACT_INTRODUCTION
        if "artist_name" in c and "created_by" in c:
            return Intent.AUTHOR_OTHER_WORKS
        if "artist_name" in c:
            return Intent.ARTIFACT_AUTHOR
        if "dynasty_name" in c and "artifact_type" in c:
            return Intent.DYNASTY_ARTIFACTS
        if "dynasty_name" in c:
            return Intent.ARTIFACT_PERIOD
        if "artifact_type" in c:
            return Intent.ARTIFACT_TYPE
        if "material" in c:
            return Intent.ARTIFACT_MATERIAL
        
        return Intent.ARTIFACT_LOCATION
