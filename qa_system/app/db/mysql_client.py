"""
app/db/mysql_client.py — MySQL 数据库客户端
【负责人：成员E】

职责：
  从 MySQL 中查询文物的详情页 URL 和其他补充信息。
  这些数据不在图谱中（图谱存关系，MySQL 存完整详情），
  由 AnswerBuilder 在组装溯源信息时调用。

为什么需要 MySQL？
  知识图谱适合存关系和核心属性，但 detail_url 等链接信息
  直接存在 MySQL 的文物表里查询更高效。连的是关系型数据库，
  存的是文物的详细信息——文物详情页的网址、图片链接等。
  这个主要是为了"答案溯源"功能，给用户附上"原始来源链接"时用到。

【MySQL 表结构（目前的）】：
  表名：artifacts
  字段：
    object_id (PK), title, artist, artist_province,
    dynasty, period, type, material, description, dimensions,
    museum, location, detail_url, image_url, image_path,
    credit_line, accession_number, crawl_date
"""

import aiomysql
from config import settings


class MySQLClient:
    """
    MySQL 异步客户端。
    
    【成员E实现】
    """

    _pool = None

    @classmethod
    async def get_pool(cls):
        """获取（或创建）MySQL 连接池"""
        if cls._pool is None:
            cls._pool = await aiomysql.create_pool(
                host=settings.MYSQL_HOST,
                port=settings.MYSQL_PORT,
                user=settings.MYSQL_USER,
                password=settings.MYSQL_PASSWORD,
                db=settings.MYSQL_DB,
                charset="utf8mb4",
                autocommit=True,
            )
        return cls._pool

    @classmethod
    async def get_artifact_detail(cls, object_id: str) -> dict:
        """
        根据文物 ID 查询详情信息（主要用于获取 detail_url）。
        
        返回示例：
          {"object_id": "CMA_1234", "detail_url": "https://...", "museum": "..."}
        
        【成员E实现】
        """
        # TODO: 成员E实现
        # pool = await cls.get_pool()
        # async with pool.acquire() as conn:
        #     async with conn.cursor(aiomysql.DictCursor) as cur:
        #         await cur.execute(
        #             "SELECT object_id, detail_url, museum FROM artifacts WHERE object_id = %s",
        #             (object_id,)
        #         )
        #         return await cur.fetchone() or {}
        return {}
