"""
app/retrieval/graph_retriever.py — 真实图谱检索器
【负责人：成员D】

职责：执行 query_builder 生成的 Cypher 语句，从真实 Neo4j 图数据库中检索数据。
      与子系统1的 Neo4j 数据库直接交互。

使用条件：config.py 中 MOCK_MODE=False 时，QAEngine 自动使用此模块。

对应架构层：知识检索层（图谱查询部分）
"""

from neo4j import AsyncGraphDatabase
from config import settings


class GraphRetriever:
    """
    Neo4j 图数据库检索器。
    
    【成员D的工作】：
    1. 实现 _get_driver() 连接池管理
    2. 实现 retrieve() 方法，执行 Cypher 并返回结果列表
    3. 实现健壮的错误处理（连接失败、查询超时、空结果等）
    4. 与子系统1对齐后，验证查询结果的字段名是否和 Mock 数据一致
    """

    def __init__(self):
        self._driver = None

    def _get_driver(self):
        """
        【成员D实现】获取（或创建）Neo4j 连接驱动。
        使用连接池避免每次查询都重新建立连接。
        """
        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                # 连接池配置，避免高并发时连接不够用
                max_connection_pool_size=10,
            )
        return self._driver

    async def retrieve(self, cypher: str, params: dict) -> list:
        """
        执行 Cypher 查询，返回结果列表。
        
        返回格式：每条记录是一个字典，字段名与 Mock 数据完全一致。
        如果查询无结果，返回空列表（上层 AnswerBuilder 处理 not_found 逻辑）。
        
        【成员D实现要点】：
        1. 用 async with driver.session() 建立会话
        2. 执行查询，将 Neo4j Record 转为普通字典
        3. 捕获所有异常，记录日志后返回空列表（不让异常传播到用户）
        """
        driver = self._get_driver()
        try:
            async with driver.session() as session:
                result = await session.run(cypher, params)
                records = await result.data()   # data() 直接返回字典列表
                return records
        except Exception as e:
            # 查询失败时记录错误但不抛出，返回空列表触发 not_found 响应
            # TODO: 成员D：替换为正式的日志记录（logging模块）
            print(f"[GraphRetriever ERROR] {e}")
            return []

    async def close(self):
        """关闭连接驱动，在应用关闭时调用"""
        if self._driver:
            await self._driver.close()
