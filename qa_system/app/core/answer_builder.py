"""
app/core/answer_builder.py — 答案组装模块
【负责人：组长】

职责：
  1. 接收图谱查询结果（来自成员D的 graph_retriever）
  2. 调用LLM生成自然语言回答（来自成员C的 llm_generator）
  3. 组装最终回答，标注溯源信息
  4. 区分"图谱事实"和"LLM生成内容"——这是课设必做要求

对应课设要求：
  - 标注数据来源博物馆
  - 提供指向原始数据详情页的链接
  - 对LLM生成的补充性描述，须与图谱事实明确区分标注
  - 对于图谱不存在的问题，明确告知"暂无相关数据"
"""

import uuid
from app.models.schemas import AskResponse, SourceInfo
from app.core.intent_types import Intent


# ── 各意图的回答模板（图谱事实部分，不经过LLM）───────────────────────────
# 这些模板把图谱查询结果格式化为结构化文本，作为"事实陈述"
# LLM 负责在此基础上润色，生成更自然的语言

FACT_TEMPLATES = {
    Intent.ARTIFACT_LOCATION: lambda r: (
        f"文物《{r.get('artifact_name', '未知')}》"
        f"现藏于{r.get('museum_name', '未知博物馆')}"
        f"（{r.get('city', '')}, {r.get('country', '')}）。"
    ),
    Intent.ARTIFACT_PERIOD: lambda r: (
        f"文物《{r.get('artifact_name', '未知')}》"
        f"属于{r.get('dynasty_name', '未知朝代')}时期"
        + (f"（{r.get('period_start_year', '')}—{r.get('period_end_year', '')}年）。"
           if r.get('period_start_year') else "。")
    ),
    Intent.ARTIFACT_MATERIAL: lambda r: (
        f"文物《{r.get('artifact_name', '未知')}》"
        f"的材质为{r.get('material', '未知材质')}，"
        f"现藏于{r.get('museum_name', '未知博物馆')}。"
    ),
    Intent.ARTIFACT_TYPE: lambda r: (
        f"文物《{r.get('artifact_name', '未知')}》"
        f"属于{r.get('artifact_type', '未知类型')}类，"
        f"现藏于{r.get('museum_name', '未知博物馆')}。"
    ),
    Intent.ARTIFACT_INTRODUCTION: lambda r: (
        f"文物《{r.get('artifact_name', '未知')}》"
        + (f"，{r.get('dynasty_name', '')}时期，" if r.get('dynasty_name') else "，")
        + (f"{r.get('artifact_type', '')}类，" if r.get('artifact_type') else "")
        + (f"{r.get('material', '')}质，" if r.get('material') else "")
        + f"现藏于{r.get('museum_name', '未知博物馆')}。"
        + (f"\n\n【原始描述】{r.get('description', '')}" if r.get('description') else "")
    ),
    Intent.ARTIFACT_AUTHOR: lambda r: (
        f"文物《{r.get('artifact_name', '未知')}》的创作者为{r.get('artist_name', '未知作者')}，"
        f"现藏于{r.get('museum_name', '未知博物馆')}。"
    ),
    Intent.AUTHOR_BIOGRAPHY: lambda r: (
        f"{r.get('artist_name', '未知艺术家')}"
        + (f"（{r.get('artist_birth', '')}—{r.get('aritist_death', '')}）"
           if r.get('artist_birth') else "")
        + (f"：{r.get('artist_bio', '')}" if r.get('artist_bio') else "，暂无详细生平记录。")
    ),
    Intent.AUTHOR_OTHER_WORKS: lambda r: (
        f"《{r.get('artifact_name', '未知')}》（{r.get('artifact_type', '')}），"
        f"藏于{r.get('museum_name', '未知博物馆')}。"
    ),
    Intent.DYNASTY_ARTIFACTS: lambda r: (
        f"《{r.get('title', r.get('artifact_name', '未知'))}》"
        f"（{r.get('type', r.get('artifact_type', ''))}），"
        f"藏于{r.get('museum_name', '未知博物馆')}。"
    ),
    Intent.ARTIFACT_DIMENSIONS: lambda r: (
        f"文物《{r.get('artifact_name', '未知')}》"
        f"的尺寸规格：{r.get('dimensions', '暂无尺寸数据')}，"
        f"现藏于{r.get('museum_name', '未知博物馆')}。"
    ),
  Intent.RELATED_ARTIFACTS: lambda r: (
    f"《{r.get('title', r.get('artifact_name', '未知'))}》"
    f"（{r.get('type', r.get('artifact_type', ''))}，"
    f"{r.get('dynasty', r.get('dynasty_name', ''))}），"
    f"材质：{r.get('material', '未知')}，"
    f"藏于{r.get('museum_name', r.get('museum', '未知博物馆'))}。"
    + (f"\n  推荐依据：{r.get('match_reason', '')}"
       if r.get('match_reason') else "")
),
}

# 列表类意图（返回多条记录，需要汇总展示）
LIST_INTENTS = {
    Intent.AUTHOR_OTHER_WORKS,
    Intent.DYNASTY_ARTIFACTS,
  Intent.RELATED_ARTIFACTS,   # 补充
}


class AnswerBuilder:
    """
    答案组装器。
    将图谱查询结果 + LLM润色 组装为标准的 AskResponse。
    """

    def __init__(self, llm_generator=None):
        """
        llm_generator: 成员C实现的 LLMGenerator 实例。
                       如果为 None，直接返回图谱事实文本，不调用LLM。
        """
        self.llm = llm_generator

    async def build(
        self,
        question: str,
        intent: str,
        entity: str,
        kg_results: list,        # 图谱查询结果（来自 graph_retriever）
    ) -> AskResponse:
        """
        组装最终回答。
        
        逻辑分支：
        1. kg_results 为空 → 返回"暂无相关数据"，not_found=True
        2. kg_results 有数据 → 格式化事实文本，调用LLM润色，组装溯源信息
        """
        answer_id = str(uuid.uuid4())[:8]

        # ── 分支1：知识图谱无数据 ─────────────────────────────────
        if not kg_results:
            return AskResponse(
                answer_id=answer_id,
                question=question,
                # 课设要求：图谱不存在的问题必须明确告知，不能让LLM编造
                answer="抱歉，知识图谱中暂无与该问题相关的数据。您可以尝试使用文物的完整名称重新提问。",
                intent=intent,
                entity=entity,
                sources=[],
                has_kg_facts=False,
                has_llm_content=False,
                not_found=True,
            )

        # ── 分支2：有图谱数据，组装事实 + 调用LLM润色 ──────────────

        # 2a. 从图谱结果中提取溯源信息（每条记录都有来源博物馆和详情页URL）
        sources = self._extract_sources(kg_results)

        # 2b. 将图谱结果格式化为事实文本（作为LLM的输入上下文）
        fact_text = self._format_facts(intent, kg_results)

        # 2c. 调用LLM润色（仅做语言表达优化，不允许添加图谱中没有的事实）
        has_llm_content = False
        if self.llm:
            final_answer = await self.llm.generate_answer(
                question=question,
                facts=fact_text,
                intent=intent,
            )
            has_llm_content = True
        else:
            # LLM 不可用时，直接返回格式化的事实文本
            final_answer = fact_text

        return AskResponse(
            answer_id=answer_id,
            question=question,
            answer=final_answer,
            intent=intent,
            entity=entity,
            sources=sources,
            has_kg_facts=True,
            has_llm_content=has_llm_content,
            not_found=False,
        )

    def _format_facts(self, intent: str, results: list) -> str:
        """
        将图谱查询结果格式化为纯文本事实描述。
        这段文字会作为LLM的上下文（不直接给用户看）。
        """
        template_fn = FACT_TEMPLATES.get(intent)
        if not template_fn:
            return str(results)

        if intent in LIST_INTENTS:
            # 列表类意图：把每条记录都格式化，然后合并
            lines = [template_fn(r) for r in results]
            return "\n".join(f"{i+1}. {line}" for i, line in enumerate(lines))
        else:
            # 单条意图：取第一条结果
            return template_fn(results[0])

    def _extract_sources(self, results: list) -> list[SourceInfo]:
        """
        从图谱结果中提取溯源信息。

        【修改说明】
        - museum_name：图谱查询结果里的别名，保持不变；
          但增加对 'museum' 字段的兜底（CSV字段名），防止字段名不一致时取空。
        - 新增填充 image_url 和 accession_number，与扩充后的 SourceInfo 对齐。
        """
        seen_ids = set()
        sources = []
        for r in results:
            obj_id = r.get("object_id", "")
            if obj_id and obj_id not in seen_ids:
                seen_ids.add(obj_id)
                sources.append(SourceInfo(
                    # 兜底：优先取图谱别名 museum_name，否则取 CSV 原始字段名 museum
                    museum_name=r.get("museum_name") or r.get("museum", "未知博物馆"),
                    detail_url=r.get("detail_url", ""),
                    object_id=obj_id,
                    image_url=r.get("image_url"),  # 新增
                    accession_number=r.get("accession_number"),  # 新增
                ))
        return sources
