"""
app/db/mysql_client.py — MySQL 数据库客户端

职责：
  从 MySQL 中查询文物信息，替代 Mock 数据，提供真实的文物数据。
  同时支持溯源信息查询（detail_url 等）。

MySQL 表结构（artifact 表，35列）：
  联合主键：(object_id, museum_id)
  核心字段：title, artist, dynasty, period, type, material, description, dimensions,
            museum, location, detail_url, image_url, accession_number ...
"""

import aiomysql
from config import settings


async def get_pool():
    return await MySQLClient.get_pool()


class MySQLClient:

    _pool = None

    @classmethod
    async def get_pool(cls):
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
    async def close_pool(cls):
        if cls._pool:
            cls._pool.close()
            await cls._pool.wait_closed()
            cls._pool = None

    @classmethod
    async def execute_query(cls, sql: str, params: tuple = ()) -> list:
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, params)
                return await cur.fetchall()

    @classmethod
    async def get_artifact_detail(cls, object_id: str) -> dict:
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """SELECT object_id, title, type, material, dynasty, period,
                              description, dimensions, museum, location,
                              detail_url, image_url, accession_number
                       FROM artifact WHERE object_id = %s""",
                    (object_id,)
                )
                return await cur.fetchone() or {}

    @classmethod
    async def search_by_title(cls, entity: str, limit: int = 5) -> list:
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """SELECT object_id, title, artist, dynasty, period,
                              type, material, culture, description, dimensions,
                              museum, location, detail_url, image_url, accession_number,
                              artist_bio, artist_birth, artist_death, artist_province
                       FROM artifact
                       WHERE title LIKE %s
                       LIMIT %s""",
                    (f"%{entity}%", limit)
                )
                return await cur.fetchall()

    @classmethod
    async def search_by_artist(cls, entity: str, limit: int = 10) -> list:
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """SELECT object_id, title, artist, dynasty, period,
                              type, material, description, dimensions,
                              museum, location, detail_url, image_url, accession_number,
                              artist_bio, artist_birth, artist_death, artist_province
                       FROM artifact
                       WHERE artist LIKE %s
                       LIMIT %s""",
                    (f"%{entity}%", limit)
                )
                return await cur.fetchall()

    @classmethod
    async def search_by_dynasty(cls, entity: str, limit: int = 10) -> list:
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """SELECT object_id, title, artist, dynasty, period,
                              type, material, description, dimensions,
                              museum, location, detail_url, image_url, accession_number
                       FROM artifact
                       WHERE dynasty LIKE %s
                       LIMIT %s""",
                    (f"%{entity}%", limit)
                )
                return await cur.fetchall()

    @classmethod
    async def search_by_museum(cls, entity: str, limit: int = 10) -> list:
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """SELECT museum, location, COUNT(*) AS artifact_count
                       FROM artifact
                       WHERE museum LIKE %s
                       GROUP BY museum, location
                       LIMIT %s""",
                    (f"%{entity}%", limit)
                )
                return await cur.fetchall()

    @classmethod
    async def get_similar_artifacts(
        cls, artifact_type: str, material: str, dynasty: str,
        exclude_object_id: str, limit: int = 10
    ) -> list:
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """SELECT object_id, title, type, material, dynasty,
                              museum, location, detail_url, image_url, accession_number,
                              CASE
                                WHEN type = %s AND material LIKE %s THEN '类型+材质相同'
                                WHEN type = %s AND dynasty LIKE %s THEN '类型+朝代相同'
                                ELSE '类型相同'
                              END AS match_reason
                       FROM artifact
                       WHERE object_id != %s AND type = %s
                       ORDER BY
                         CASE
                           WHEN type = %s AND material LIKE %s THEN 1
                           WHEN type = %s AND dynasty LIKE %s THEN 2
                           ELSE 3
                         END
                       LIMIT %s""",
                    (
                        artifact_type, f"%{material}%",
                        artifact_type, f"%{dynasty}%",
                        exclude_object_id, artifact_type,
                        artifact_type, f"%{material}%",
                        artifact_type, f"%{dynasty}%",
                        limit,
                    )
                )
                return await cur.fetchall()
