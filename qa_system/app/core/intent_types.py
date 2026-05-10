"""
app/core/intent_types.py — 意图类型定义

集中定义所有支持的问题意图，对应课设要求的10类简单问答。
整个项目统一使用这里的常量，避免各模块用字符串硬编码。

成员A（intent_parser.py）负责识别出哪个意图。
成员B（query_builder.py）根据意图选择对应的 Cypher 模板。
"""


class Intent:
    # ── 课设必做的10类问答 ─────────────────────────────────────

    # 文物收藏地：该文物现藏于哪家博物馆？
    ARTIFACT_LOCATION = "artifact_location"

    # 文物年代：该文物属于哪个历史时期？
    ARTIFACT_PERIOD = "artifact_period"

    # 文物材质：该文物由什么材料制成？
    ARTIFACT_MATERIAL = "artifact_material"

    # 文物类型：该文物属于哪种器物类别？
    ARTIFACT_TYPE = "artifact_type"

    # 文物介绍：请介绍一下这件文物。
    ARTIFACT_INTRODUCTION = "artifact_introduction"

    # 书画作者：该书画作品的作者是谁？
    ARTIFACT_AUTHOR = "artifact_author"

    # 作者生平：该作者的生平经历是怎样的？
    AUTHOR_BIOGRAPHY = "author_biography"

    # 同一作者作品：该作者还有哪些作品被海外博物馆收藏？
    AUTHOR_OTHER_WORKS = "author_other_works"

    # 同一朝代文物：某朝代有哪些代表性文物？
    DYNASTY_ARTIFACTS = "dynasty_artifacts"

    # 文物尺寸与规格：该文物的尺寸和重量是多少？
    ARTIFACT_DIMENSIONS = "artifact_dimensions"

    # ── 兜底 ───────────────────────────────────────────────────

    # 无法识别的问题，返回"暂无相关数据"
    UNKNOWN = "unknown"

    @classmethod
    def all_known(cls) -> list:
        """返回所有已知意图（不含UNKNOWN），用于LLM Prompt中列举"""
        return [
            cls.ARTIFACT_LOCATION,
            cls.ARTIFACT_PERIOD,
            cls.ARTIFACT_MATERIAL,
            cls.ARTIFACT_TYPE,
            cls.ARTIFACT_INTRODUCTION,
            cls.ARTIFACT_AUTHOR,
            cls.AUTHOR_BIOGRAPHY,
            cls.AUTHOR_OTHER_WORKS,
            cls.DYNASTY_ARTIFACTS,
            cls.ARTIFACT_DIMENSIONS,
        ]
