"""
app/agents/tools/mysql_tool.py — MySQL 工具

提供数据库查询能力，支持：
1. Schema 预览
2. 安全的 SQL 执行（SELECT only with LIMIT）
3. SQL 注入防护

数据库：overseas_chinese_artifacts
表：artifact（共 6997 条记录，35 个字段）
"""

import json
import re
import aiomysql
from config import settings


SCHEMA_INFO = """
## MySQL 数据库 Schema（overseas_chinese_artifacts.artifact 表）

表名：artifact，记录数：6997

### 字段列表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| object_id | VARCHAR(255) | 主键，唯一标识符 |
| artifact_id | VARCHAR(256) | 实体ID（有索引） |
| museum_id | INT | 博物馆ID |
| title | VARCHAR(500) | 文物英文名称（如 A Song、Blue and White Vase） |
| artist | VARCHAR(500) | 创作者（英文，多人用分号分隔） |
| artist_province | VARCHAR(100) | 艺术家省份 |
| dynasty | VARCHAR(200) | 朝代（中英文混合，如 Qing（清）、Tang（唐）） |
| artist_wikidata_id | VARCHAR(32) | 艺术家 Wikidata ID |
| artist_birth | VARCHAR(120) | 艺术家出生年份 |
| artist_death | VARCHAR(120) | 艺术家去世年份 |
| artist_bio | VARCHAR(4000) | 艺术家简介 |
| artist_wikipedia_summary | VARCHAR(4000) | 维基百科摘要 |
| period | VARCHAR(200) | 创作时期（如 1890s、18th century） |
| period_start_year | SMALLINT | 起始年份 |
| period_end_year | SMALLINT | 结束年份 |
| type | VARCHAR(100) | 文物类型（Paintings、Ceramics、Sculptures、Bronzes 等） |
| material | TEXT | 材质/媒介描述 |
| culture | VARCHAR(300) | 文化/主题标签 |
| description | TEXT | 描述文本 |
| provenance | TEXT | 出土/流传信息 |
| bibliography | TEXT | 参考文献 |
| dimensions | TEXT | 尺寸（如 35 x 22 cm） |
| museum | VARCHAR(300) | 所属博物馆名称 |
| location | VARCHAR(300) | 博物馆所在城市/国家 |
| detail_url | TEXT | 文物详情页 URL（溯源用） |
| image_url | TEXT | 主图 URL |
| image_urls | TEXT | 所有图片 URL |
| iiif_manifest_url | TEXT | IIIF Manifest URL |
| accession_number | VARCHAR(200) | 登记号 |
| credit_line | TEXT | 藏品说明/捐赠信息 |
| crawl_date | DATE | 爬取日期 |

### 索引
- object_id：主键
- artifact_id：有索引（MUL）

### 查询示例
- 按博物馆统计：`SELECT museum, COUNT(*) as cnt FROM artifact GROUP BY museum ORDER BY cnt DESC LIMIT 10`
- 按朝代查询：`SELECT DISTINCT dynasty FROM artifact LIMIT 100`
- 搜索文物：`SELECT object_id, title, artist, dynasty, museum, detail_url FROM artifact WHERE museum LIKE '%British Museum%' LIMIT 20`
- 获取详情：`SELECT * FROM artifact WHERE object_id = 'xxx' LIMIT 1`
"""


_pool = None

ALLOWED_TABLES = ["artifact"]
ALLOWED_OPERATIONS = ["SELECT"]
FORBIDDEN_KEYWORDS = [
    r"\bDROP\b", r"\bDELETE\b", r"\bUPDATE\b", r"\bINSERT\b",
    r"\bALTER\b", r"\bCREATE\b", r"\bTRUNCATE\b", r"\bGRANT\b",
    r"\bREVOKE\b", r"\bEXEC\b", r"\bEXECUTE\b", r"\bUNION\b",
    r";\s*", r"--", r"/\*", r"\bOR\s+1\s*=\s*1", r"\bAND\s+1\s*=\s*1",
]

MAX_LIMIT = 100
DEFAULT_LIMIT = 10


async def get_pool():
    global _pool
    if _pool is None:
        _pool = await aiomysql.create_pool(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            db=settings.MYSQL_DB,
            charset="utf8mb4",
            autocommit=True,
        )
    return _pool


async def close_pool():
    global _pool
    if _pool:
        _pool.close()
        await _pool.wait_closed()
        _pool = None


def validate_sql(sql: str) -> tuple[bool, str]:
    """
    验证 SQL 语句的安全性。
    只允许 SELECT 操作，并检查危险的 SQL 模式。
    """
    sql_upper = sql.upper().strip()

    if not sql_upper.startswith("SELECT"):
        return False, "只允许 SELECT 查询操作"

    for pattern in FORBIDDEN_KEYWORDS:
        if re.search(pattern, sql, re.IGNORECASE):
            return False, f"禁止使用可疑关键字: {pattern}"

    if "limit" not in sql_lower(sql):
        return False, "必须指定 LIMIT 限制返回行数"

    limit_match = re.search(r"limit\s+(\d+)", sql_lower(sql))
    if limit_match:
        limit_val = int(limit_match.group(1))
        if limit_val > MAX_LIMIT:
            return False, f"LIMIT 不能超过 {MAX_LIMIT}"

    return True, "OK"


def sql_lower(sql: str) -> str:
    """将 SQL 关键字转换为小写（保留字符串内的大小写）"""
    parts = []
    in_string = False
    string_char = None
    for char in sql:
        if not in_string and char in ("'", '"'):
            in_string = True
            string_char = char
        elif in_string and char == string_char:
            in_string = False
            string_char = None
        elif not in_string:
            parts.append(char.lower())
        else:
            parts.append(char)
    return "".join(parts)


async def get_schema() -> str:
    """获取数据库 Schema 信息"""
    return SCHEMA_INFO


async def execute_sql(query: str, params: tuple = ()) -> str:
    """
    执行安全的 SQL 查询。

    Args:
        query: SQL 查询语句（必须是 SELECT，以 LIMIT 结尾）
        params: 查询参数（元组）

    Returns:
        JSON 格式的查询结果
    """
    import logging
    logging.info(f"[MySQL] execute_sql called")
    logging.info(f"[MySQL] Query: {query}")
    logging.info(f"[MySQL] Params: {params}")
    logging.info(f"[MySQL] Params type: {type(params)}")

    if not query or len(query.strip()) == 0:
        return json.dumps({"error": "查询语句不能为空"})

    is_valid, msg = validate_sql(query)
    if not is_valid:
        logging.warning(f"[MySQL] SQL validation failed: {msg}")
        return json.dumps({"error": f"SQL 验证失败: {msg}"})

    pool = await get_pool()
    try:
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                logging.info(f"[MySQL] Executing query...")
                try:
                    await cur.execute(query, params if params else None)
                except Exception as exec_err:
                    logging.error(f"[MySQL] Execute failed: {exec_err}")
                    logging.error(f"[MySQL] Query was: {query}")
                    raise
                rows = await cur.fetchall()

                logging.info(f"[MySQL] Query executed successfully")
                logging.info(f"[MySQL] Returned {len(rows)} rows")
                if rows:
                    logging.info(f"[MySQL] First row keys: {list(rows[0].keys()) if rows else []}")
                    logging.info(f"[MySQL] First row sample: {rows[0] if rows else None}")

                if not rows:
                    return json.dumps([], ensure_ascii=False)

                return json.dumps(rows, ensure_ascii=False, default=str)
    except Exception as e:
        error_msg = str(e)
        logging.error(f"[MySQL] Query failed: {error_msg}")
        if "MySQL server has gone away" in error_msg:
            return json.dumps({"error": "数据库连接超时，请重试"})
        if "Lock wait timeout" in error_msg:
            return json.dumps({"error": "查询执行超时，请简化查询条件"})
        return json.dumps({"error": f"查询执行失败: {error_msg}"})


async def quick_search(keyword: str, field: str = "title", limit: int = 10) -> str:
    """
    快速搜索辅助函数，支持多字段搜索。

    Args:
        keyword: 搜索关键词
        field: 搜索字段 (title/artist/dynasty/museum/type)
        limit: 返回数量

    Returns:
        JSON 格式的搜索结果
    """
    allowed_fields = ["title", "artist", "dynasty", "museum", "type", "description"]
    if field not in allowed_fields:
        field = "title"

    safe_field = field.replace("`", "").replace("'", "")

    limit = min(limit, MAX_LIMIT)
    query = f"SELECT object_id, title, artist, dynasty, type, museum, location, image_url, detail_url FROM artifact WHERE `{safe_field}` LIKE %s LIMIT %s"

    return await execute_sql(query, (f"%{keyword}%", limit))