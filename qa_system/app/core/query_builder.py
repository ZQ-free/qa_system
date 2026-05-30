"""
app/core/query_builder.py — 查询构建模块

职责：根据意图类型和实体名称，生成查询配置。
当前阶段 MySQLRetriever 通过 Cypher 字符串推断意图，然后执行对应的 MySQL 查询。
后续对接 Neo4j 时，Cypher 模板将直接用于图数据库查询。

Schema 对齐文档：app/schema_agreement.md
"""

from app.core.intent_types import Intent


CYPHER_TEMPLATES = {

    Intent.ARTIFACT_LOCATION: """
        MATCH (a:Artifact)-[:COLLECTED_BY]->(m:Museum)
        WHERE toLower(a.title) CONTAINS toLower($entity)
        RETURN a.title AS artifact_name, a.object_id AS object_id,
               a.detail_url AS detail_url, a.image_url AS image_url,
               a.accession_number AS accession_number,
               m.name AS museum_name, m.city AS city, m.country AS country
        LIMIT 5
    """,

    Intent.ARTIFACT_PERIOD: """
        MATCH (a:Artifact)
        WHERE toLower(a.title) CONTAINS toLower($entity)
           OR toLower(a.dynasty) CONTAINS toLower($entity)
        OPTIONAL MATCH (a)-[:COLLECTED_BY]->(m:Museum)
        RETURN a.title AS artifact_name, a.object_id AS object_id,
               a.detail_url AS detail_url,
               a.dynasty AS dynasty_name, a.period AS period,
               m.name AS museum_name
        LIMIT 5
    """,

    Intent.ARTIFACT_MATERIAL: """
        MATCH (a:Artifact)
        WHERE toLower(a.title) CONTAINS toLower($entity)
        OPTIONAL MATCH (a)-[:COLLECTED_BY]->(m:Museum)
        RETURN a.title AS artifact_name, a.object_id AS object_id,
               a.detail_url AS detail_url,
               a.material AS material, m.name AS museum_name
        LIMIT 5
    """,

    Intent.ARTIFACT_TYPE: """
        MATCH (a:Artifact)
        WHERE toLower(a.title) CONTAINS toLower($entity)
        OPTIONAL MATCH (a)-[:COLLECTED_BY]->(m:Museum)
        RETURN a.title AS artifact_name, a.object_id AS object_id,
               a.detail_url AS detail_url,
               a.type AS artifact_type, m.name AS museum_name
        LIMIT 5
    """,

    Intent.ARTIFACT_INTRODUCTION: """
        MATCH (a:Artifact)
        WHERE toLower(a.title) CONTAINS toLower($entity)
        OPTIONAL MATCH (a)-[:COLLECTED_BY]->(m:Museum)
        RETURN a.title AS artifact_name, a.object_id AS object_id,
               a.detail_url AS detail_url,
               a.description AS description, a.type AS artifact_type,
               a.material AS material, a.dynasty AS dynasty_name,
               m.name AS museum_name
        LIMIT 5
    """,

    Intent.ARTIFACT_AUTHOR: """
        MATCH (a:Artifact)
        WHERE toLower(a.title) CONTAINS toLower($entity)
        OPTIONAL MATCH (a)-[:CREATED_BY]->(ar:Artist)
        OPTIONAL MATCH (a)-[:COLLECTED_BY]->(m:Museum)
        RETURN a.title AS artifact_name, a.object_id AS object_id,
               a.detail_url AS detail_url,
               a.artist AS artist_name, m.name AS museum_name
        LIMIT 5
    """,

    Intent.AUTHOR_BIOGRAPHY: """
        MATCH (a:Artifact)
        WHERE toLower(a.artist) CONTAINS toLower($entity)
        RETURN DISTINCT a.artist AS artist_name,
               a.artist_bio AS artist_bio,
               a.artist_birth AS artist_birth,
               a.artist_death AS artist_death,
               a.artist_province AS artist_province
        LIMIT 1
    """,

    Intent.AUTHOR_OTHER_WORKS: """
        MATCH (a:Artifact)
        WHERE toLower(a.artist) CONTAINS toLower($entity)
        OPTIONAL MATCH (a)-[:COLLECTED_BY]->(m:Museum)
        RETURN a.title AS artifact_name, a.object_id AS object_id,
               a.detail_url AS detail_url,
               a.type AS artifact_type, m.name AS museum_name
        LIMIT 10
    """,

    Intent.DYNASTY_ARTIFACTS: """
        MATCH (a:Artifact)
        WHERE toLower(a.dynasty) CONTAINS toLower($entity)
        OPTIONAL MATCH (a)-[:COLLECTED_BY]->(m:Museum)
        RETURN a.title AS artifact_name, a.object_id AS object_id,
               a.detail_url AS detail_url,
               a.type AS artifact_type, a.dynasty AS dynasty_name,
               m.name AS museum_name
        LIMIT 10
    """,

    Intent.ARTIFACT_DIMENSIONS: """
        MATCH (a:Artifact)
        WHERE toLower(a.title) CONTAINS toLower($entity)
        OPTIONAL MATCH (a)-[:COLLECTED_BY]->(m:Museum)
        RETURN a.title AS artifact_name, a.object_id AS object_id,
               a.detail_url AS detail_url,
               a.dimensions AS dimensions, m.name AS museum_name
        LIMIT 5
    """,

    Intent.ARTIFACT_RECOMMEND: """
        MATCH (a:Artifact)
        WHERE toLower(a.title) CONTAINS toLower($entity)
        WITH a LIMIT 1
        MATCH (rec:Artifact)
        WHERE rec.object_id <> a.object_id AND rec.type = a.type
        OPTIONAL MATCH (rec)-[:COLLECTED_BY]->(m:Museum)
        RETURN rec.title AS title, rec.object_id AS object_id,
               rec.detail_url AS detail_url,
               rec.type AS type, rec.material AS material,
               rec.dynasty AS dynasty, m.name AS museum_name
        ORDER BY
          CASE
            WHEN rec.material = a.material THEN 1
            WHEN rec.dynasty = a.dynasty THEN 2
            ELSE 3
          END
        LIMIT 10
    """,
}


class QueryBuilder:

    def build(self, intent: str, entity: str) -> dict:
        if intent == Intent.UNKNOWN or intent not in CYPHER_TEMPLATES:
            return None

        cypher = CYPHER_TEMPLATES[intent].strip()

        return {
            "cypher": cypher,
            "params": {"entity": entity},
            "intent": intent,
            "entity": entity,
        }
