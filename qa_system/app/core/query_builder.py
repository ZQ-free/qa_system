"""
app/core/query_builder.py — Cypher 查询构建模块
【负责人：成员B】

职责：根据意图类型和实体名称，生成对应的 Neo4j Cypher 查询语句。

这是与子系统1对接最紧密的模块：
  - 节点标签名（如 Artifact、Museum）来自子系统1
  - 属性名（如 name、type）来自子系统1
  - 关系类型名（如 COLLECTED_BY）来自子系统1

【重要】当前使用假定的 schema，与子系统1对齐后只需修改本文件的常量区域。

假定的 Schema（等待与子系统1确认）：
  节点：Artifact(name, object_id, type, material, dimensions, description, image_url, detail_url)
        Museum(name, city, country)
        Dynasty(name, start_year, end_year)
        Artist(name, bio, birth_year, death_year)
  关系：(Artifact)-[:COLLECTED_BY]->(Museum)
        (Artifact)-[:BELONGS_TO_DYNASTY]->(Dynasty)
        (Artifact)-[:CREATED_BY]->(Artist)
        (Artifact)-[:MADE_OF {material}]->(Material) 或直接 Artifact.material 属性
"""

from app.core.intent_types import Intent


# ══════════════════════════════════════════════════════════════════════════════
# Schema 常量区域（与子系统1对齐后只改这里）
# ══════════════════════════════════════════════════════════════════════════════
NODE_ARTIFACT = "Artifact"
NODE_MUSEUM   = "Museum"
NODE_DYNASTY  = "Dynasty"
NODE_ARTIST   = "Artist"

PROP_NAME        = "name"
PROP_OBJECT_ID   = "object_id"
PROP_TYPE        = "type"
PROP_MATERIAL    = "material"
PROP_DIMENSIONS  = "dimensions"
PROP_DESCRIPTION = "description"
PROP_DETAIL_URL  = "detail_url"

REL_COLLECTED_BY    = "COLLECTED_BY"
REL_BELONGS_TO      = "BELONGS_TO_DYNASTY"
REL_CREATED_BY      = "CREATED_BY"

# ══════════════════════════════════════════════════════════════════════════════
# Cypher 模板（每种意图对应一个查询语句）
# ══════════════════════════════════════════════════════════════════════════════

CYPHER_TEMPLATES = {

    # 文物收藏地：找到文物节点，沿 COLLECTED_BY 关系找到博物馆，返回博物馆信息
    Intent.ARTIFACT_LOCATION: """
        MATCH (a:{artifact})-[:{rel}]->(m:{museum})
        WHERE toLower(a.{name}) CONTAINS toLower($entity)
        RETURN a.{name} AS artifact_name, a.{obj_id} AS object_id, 
               a.{url} AS detail_url,
               m.{name} AS museum_name, m.city AS city, m.country AS country
        LIMIT 5
    """.format(
        artifact=NODE_ARTIFACT, rel=REL_COLLECTED_BY, museum=NODE_MUSEUM,
        name=PROP_NAME, obj_id=PROP_OBJECT_ID, url=PROP_DETAIL_URL
    ),

}


class QueryBuilder:
    """
    Cypher 查询语句构建器。
    
    【成员B的工作】：
    1. 当前模板已基于假定 schema 写好，可直接运行（配合 mock_retriever）
    2. 与子系统1对齐后：修改文件顶部的常量区域，模板会自动更新
    3. 选做功能（复杂多跳查询）：在此文件添加新的意图模板
    """

    def build(self, intent: str, entity: str) -> dict:
        """
        根据意图和实体，返回可执行的查询配置。
        
        返回：
          {
            "cypher": "MATCH ...",     # Cypher 语句
            "params": {"entity": ...}, # 查询参数（防注入）
            "intent": "...",
            "entity": "..."
          }
        
        如果意图是 UNKNOWN 或没有对应模板，返回 None。
        """
        if intent == Intent.UNKNOWN or intent not in CYPHER_TEMPLATES:
            return None

        cypher = CYPHER_TEMPLATES[intent].strip()

        return {
            "cypher": cypher,
            "params": {"entity": entity},
            "intent": intent,
            "entity": entity,
        }
