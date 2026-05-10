"""
app/db/neo4j_client.py — Neo4j 数据库客户端封装
【负责人：成员E】
文件功能：连的是图数据库，存的是关系——谁收藏了谁、谁创作了谁、属于哪个朝代。查文物关系走这个。
职责：
  提供底层 Neo4j 连接管理。GraphRetriever 通过此模块执行查询。
  将数据库连接细节从业务逻辑中隔离出来。

成员E还需实现：
  - mysql_client.py：封装 MySQL 文物详情查询
  - session_store.py：封装多轮对话上下文存储（选做预留）

【与子系统1的对接点】：
  子系统1提供 Neo4j 连接地址、用户名、密码后，在 .env 中更新即可，
  此模块代码不需要任何改动。
"""

from neo4j import AsyncGraphDatabase
from config import settings


class Neo4jClient:
    """
    Neo4j 异步客户端，管理连接池。
    
    【成员E实现】
    当前 GraphRetriever 已经包含连接逻辑，此文件作为额外的工具层，
    可以提供：
    - 连接健康检查
    - 批量查询
    - 事务支持（如果后续选做需要写入操作）
    """

    _instance = None   # 单例，整个应用共用一个连接池

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            )
        return cls._instance

    @classmethod
    async def verify_connectivity(cls) -> bool:
        """
        验证 Neo4j 连接是否正常。
        应用启动时或与子系统1联调时调用。
        """
        try:
            driver = cls.get_instance()
            await driver.verify_connectivity()
            return True
        except Exception as e:
            print(f"[Neo4j] 连接失败: {e}")
            return False
