# app/models/schemas.py

from pydantic import BaseModel
from typing import Optional

# ══════════════════════════════════════════════
# 【新增】文物数据模型 —— 对应 CSV 的完整字段
# 用于 mysql_client 返回值的类型约束，以及前端展示
# ══════════════════════════════════════════════

class Artifact(BaseModel):
    """
    对应 MySQL artifacts 表的完整字段。
    字段名与 CSV 表头保持一致，方便导入时直接映射。
    所有字段除 object_id 外均为 Optional，因为爬取数据存在缺失。
    """
    object_id: str
    title: Optional[str] = None
    artist: Optional[str] = None
    artist_province: Optional[str] = None   # 新增：艺术家籍贯，CSV 有此字段
    dynasty: Optional[str] = None
    period: Optional[str] = None            # 新增：比 dynasty 更细的时期描述
    type: Optional[str] = None
    material: Optional[str] = None
    description: Optional[str] = None
    dimensions: Optional[str] = None
    museum: Optional[str] = None
    location: Optional[str] = None          # 新增：如 "Cambridge, MA, USA"
    detail_url: Optional[str] = None
    image_url: Optional[str] = None
    image_path: Optional[str] = None        # 新增：本地图片路径
    credit_line: Optional[str] = None       # 新增：版权/捐赠信息
    accession_number: Optional[str] = None  # 新增：馆藏编号，如 "1943.50.434"
    crawl_date: Optional[str] = None        # 新增：爬取日期


# ══════════════════════════════════════════════
# 请求模型（不变）
# ══════════════════════════════════════════════

class AskRequest(BaseModel):
    question: str
    session_id: Optional[str] = None

class FeedbackRequest(BaseModel):
    answer_id: str
    is_helpful: bool


# ══════════════════════════════════════════════
# 响应模型
# ══════════════════════════════════════════════

class SourceInfo(BaseModel):
    """
    答案溯源信息。
    【修改】新增 image_url 和 accession_number，
    image_url 供前端展示文物缩略图，accession_number 是标准馆藏编号引用。
    """
    museum_name: str
    detail_url: str
    object_id: str
    image_url: Optional[str] = None         # 新增
    accession_number: Optional[str] = None  # 新增

class AskResponse(BaseModel):               # 完全不变
    answer_id: str
    question: str
    answer: str
    intent: str
    entity: str
    sources: list[SourceInfo]
    has_kg_facts: bool
    has_llm_content: bool
    not_found: bool