# app/models/schemas.py

from pydantic import BaseModel
from typing import Optional

# ══════════════════════════════════════════════
# 文物数据模型 —— 对应 MySQL artifact 表的完整 31 个字段
# 用于 mysql_client 返回值的类型约束，以及前端展示
# ══════════════════════════════════════════════

class Artifact(BaseModel):
    """
    严格对应 MySQL artifact 表的完整字段（35列）。
    字段名与建表语句保持一致。

    主键说明：
      数据库联合主键为 (object_id, museum_id)，
      museum_id: 1=史密森尼  2=哈佛  3=波士顿MFA（依团组实际分配调整）

    字段分组：
      - 文物基础信息：object_id / artifact_id / museum_id / title / type / material / culture
      - 时间信息：dynasty / period / period_start_year / period_end_year
      - 作者信息：artist / artist_province / artist_wikidata_id /
                  artist_birth / artist_death / artist_bio /
                  artist_wikipedia_summary / artist_enriched_at
      - 详细描述：description / provenance / bibliography / dimensions
      - 馆藏信息：museum / location / accession_number / credit_line
      - URL与路径：detail_url / image_url / image_urls / iiif_manifest_url / image_path / image_paths
      - 图片元数据：image_count
      - 爬取元数据：crawl_date
    """

    # ── 联合主键 ──────────────────────────────────────────────────
    object_id: str                              # 文物唯一编号（馆方/EDAN）
    artifact_id: Optional[str] = None           # 文物内部编号
    museum_id: int                              # 馆别编号（联合主键，不可缺失）

    # ── 文物基础信息 ──────────────────────────────────────────────
    title: Optional[str] = None                 # 文物名称
    type: Optional[str] = None                  # 文物类型，如 Painting / Ceramics
    material: Optional[str] = None              # 材质，如 Silk / Bronze / Jade
    culture: Optional[str] = None               # 文化/地域标签，如 "Chinese"

    # ── 时间信息 ──────────────────────────────────────────────────
    dynasty: Optional[str] = None               # 朝代，如 "Tang Dynasty"
    period: Optional[str] = None                # 年代/时期原文，比 dynasty 更细
    period_start_year: Optional[int] = None     # 起始年（整数，用于范围查询/时间轴）
    period_end_year: Optional[int] = None       # 结束年

    # ── 作者信息 ──────────────────────────────────────────────────
    artist: Optional[str] = None                # 作者/制作者
    artist_province: Optional[str] = None       # 作者相关省份（推断）
    artist_wikidata_id: Optional[str] = None    # Wikidata Q号，用于实体对齐
    artist_birth: Optional[str] = None          # 作者生年
    artist_death: Optional[str] = None          # 作者卒年
    artist_bio: Optional[str] = None            # 作者简介（百科补充）
    artist_wikipedia_summary: Optional[str] = None  # 维基百科摘要
    artist_enriched_at: Optional[str] = None    # 作者信息补全时间戳

    # ── 详细描述 ──────────────────────────────────────────────────
    description: Optional[str] = None           # 文物介绍（爬取原始描述）
    provenance: Optional[str] = None            # 流传经历
    bibliography: Optional[str] = None          # 参考文献
    dimensions: Optional[str] = None            # 尺寸，如 "H. 30 cm × W. 20 cm"

    # ── 馆藏信息 ──────────────────────────────────────────────────
    museum: Optional[str] = None                # 所属博物馆完整英文名
    location: Optional[str] = None             # 博物馆所在地，如 "Cambridge, MA, USA"
    accession_number: Optional[str] = None      # 藏品编号，如 "1943.50.434"
    credit_line: Optional[str] = None           # 版权/来源说明

    # ── URL 与本地路径 ────────────────────────────────────────────
    detail_url: Optional[str] = None            # 文物详情页 URL
    image_url: Optional[str] = None             # 图片原始下载链接（原图，非缩略图）
    iiif_manifest_url: Optional[str] = None     # IIIF manifest URL（哈佛特有）
    image_path: Optional[str] = None            # 本地相对图片路径
    image_urls: Optional[str] = None            # 多图片URL（JSON数组）
    image_paths: Optional[str] = None           # 多图片本地路径（JSON数组）
    image_count: int = 0                        # 图片数量

    # ── 爬取元数据 ────────────────────────────────────────────────
    crawl_date: Optional[str] = None            # 爬取日期，格式 YYYY-MM-DD


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
    新增 image_url 和 accession_number：
      - image_url：供前端展示文物缩略图；
      - accession_number：标准馆藏编号，便于用户引用原始馆藏记录。
    """
    museum_name: str
    detail_url: str
    object_id: str
    image_url: Optional[str] = None
    accession_number: Optional[str] = None


class AskResponse(BaseModel):
    answer_id: str
    question: str
    answer: str
    intent: str
    entity: str
    sources: list[SourceInfo]
    has_kg_facts: bool
    has_llm_content: bool
    not_found: bool
