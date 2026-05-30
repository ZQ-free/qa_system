"""
Neo4j Tool — 将图数据库查询封装为 LangChain Tool
Graph Agent 通过调用此 Tool 执行 Cypher 语句，获取查询结果。
仅在 ENABLE_NEO4J=on 时才注册给 Agent。
"""

import json
from typing import Optional
from langchain_core.tools import tool
from config import settings

_neo4j_driver = None

NEO4J_SCHEMA_INFO = """
## Neo4j 知识图谱 Schema（暂未接入，待 ENABLE_NEO4J=on 后更新）

节点类型：
- Artifact（文物）
- Museum（博物馆）
- Artist（艺术家）

关系类型：
- (Artifact)-[:COLLECTED_BY]->(Museum)
- (Artifact)-[:CREATED_BY]->(Artist)

注意：Neo4j 当前为 OFF 状态，Schema 信息待连接成功后补充。
"""


def _get_driver():
    global _neo4j_driver
    if _neo4j_driver is None:
        from neo4j import AsyncGraphDatabase
        _neo4j_driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            max_connection_pool_size=10,
        )
    return _neo4j_driver


async def close_driver():
    global _neo4j_driver
    if _neo4j_driver:
        await _neo4j_driver.close()
        _neo4j_driver = None


def is_neo4j_enabled() -> bool:
    return settings.ENABLE_NEO4J


@tool
async def query_neo4j(cypher: str, params: Optional[str] = None) -> str:
    """
    执行 Cypher 查询语句，从文物知识图谱中检索数据。

    Args:
        cypher: 合法的 Cypher 查询语句
        params: JSON 格式的查询参数字符串，例如 '{"entity": "青花瓷"}'

    Returns:
        查询结果的 JSON 字符串，如果无结果返回空列表 '[]'，
        如果查询出错返回错误信息字符串。
    """
    if not settings.ENABLE_NEO4J:
        return json.dumps({"error": "Neo4j 工具未启用（ENABLE_NEO4J=off）"}, ensure_ascii=False)

    parsed_params = {}
    if params:
        try:
            parsed_params = json.loads(params)
        except json.JSONDecodeError:
            return json.dumps({"error": f"参数 JSON 解析失败: {params}"}, ensure_ascii=False)

    driver = _get_driver()
    try:
        async with driver.session() as session:
            result = await session.run(cypher, parsed_params)
            records = await result.data()
            return json.dumps(records, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": f"Cypher 执行失败: {str(e)}"}, ensure_ascii=False)


@tool
async def get_graph_schema() -> str:
    """
    获取当前知识图谱的 Schema 信息，包括节点类型、属性、关系类型。
    在生成 Cypher 查询之前调用此工具了解图谱结构。

    Returns:
        图谱 Schema 的文本描述
    """
    return NEO4J_SCHEMA_INFO


@tool
async def explore_graph_sample(node_label: str) -> str:
    """
    查看某个节点类型的样本数据，了解实际数据格式。

    Args:
        node_label: 节点标签，如 'Artifact', 'Museum', 'Artist'

    Returns:
        该类型节点的前 3 条样本数据
    """
    if not settings.ENABLE_NEO4J:
        return json.dumps({"error": "Neo4j 工具未启用（ENABLE_NEO4J=off）"}, ensure_ascii=False)

    allowed_labels = {"Artifact", "Museum", "Artist"}
    if node_label not in allowed_labels:
        return json.dumps({"error": f"不允许的节点标签: {node_label}"}, ensure_ascii=False)

    cypher = f"MATCH (n:{node_label}) RETURN n LIMIT 3"
    driver = _get_driver()
    try:
        async with driver.session() as session:
            result = await session.run(cypher)
            records = await result.data()
            return json.dumps(records, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)