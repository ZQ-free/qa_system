"""
app/core/answer_builder.py — 答案组装模块

职责：
  1. 接收 Graph Agent 查询结果（包含自然语言回答 + 溯源信息）
  2. 调用LLM进一步润色回答
  3. 组装最终回答，标注溯源信息
  4. 区分"图谱事实"和"LLM生成内容"——这是课设必做要求

对应课设要求：
  - 标注数据来源博物馆
  - 提供指向原始数据详情页的链接
  - 对LLM生成的补充性描述，须与图谱事实明确区分标注
  - 对于图谱不存在的问题，明确告知"暂无相关数据"
"""

import json
import uuid
import re
from app.models.schemas import AskResponse, SourceInfo


class AnswerBuilder:
    """
    答案组装器。
    将 Graph Agent 查询结果 + LLM润色 组装为标准的 AskResponse。
    """

    def __init__(self, llm_generator=None):
        self.llm = llm_generator

    async def build(
        self,
        question: str,
        intent: str,
        entity: str,
        kg_results: list,
        intermediate_steps: list = None,
    ) -> AskResponse:
        """
        组装最终回答。

        kg_results: 来自 Graph Agent 的结果列表，每项含 text 和 source
        intermediate_steps: Agent 的中间步骤，用于提取溯源信息
        """
        answer_id = str(uuid.uuid4())[:8]

        # ── 解析 Graph Agent 返回的文本答案 ──────────────────────
        graph_text = ""
        for r in kg_results:
            if isinstance(r, dict):
                graph_text = r.get("text", "")
            else:
                graph_text = str(r)
            break

        graph_text = graph_text.strip()

        # ── 从 intermediate_steps 提取溯源信息 ────────────────────
        sources = []
        if intermediate_steps:
            sources = self._extract_sources_from_steps(intermediate_steps)

        # ── 判断是否有实质内容 ────────────────────────────────────
        no_data_phrases = [
            "暂无相关数据",
            "未找到",
            "数据库中暂无",
            "知识图谱中暂无",
            "no relevant data",
            "not found",
            "error",
        ]
        is_empty = not graph_text or any(
            phrase in graph_text.lower() for phrase in no_data_phrases
        )

        if is_empty:
            return AskResponse(
                answer_id=answer_id,
                question=question,
                answer="抱歉，数据库中暂无与该问题相关的数据。您可以尝试提供更完整的文物名称或使用英文关键词重新提问。",
                intent=intent,
                entity=entity,
                sources=sources,
                has_kg_facts=False,
                has_llm_content=False,
                not_found=True,
            )

        # ── LLM 润色（可选）──────────────────────────────────────
        has_llm_content = False
        if self.llm and graph_text:
            final_answer = await self.llm.generate_answer(
                question=question,
                facts=graph_text,
                intent=intent,
            )
            has_llm_content = True
        else:
            final_answer = graph_text

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

    def _extract_sources_from_steps(self, steps: list) -> list[SourceInfo]:
        """
        从 Agent 的 intermediate_steps 中提取溯源信息。
        steps 格式: [(AgentAction, ToolResult), ...]
        从 Tool 返回的 JSON 中解析 object_id、detail_url、image_url 等字段。
        """
        seen_ids = set()
        sources = []

        for step in steps:
            if not isinstance(step, (list, tuple)) or len(step) < 2:
                continue

            tool_name = ""
            tool_output = ""

            if hasattr(step[0], "tool"):
                tool_name = step[0].tool
                tool_output = step[1] if isinstance(step[1], str) else str(step[1])
            elif isinstance(step[0], dict):
                tool_name = step[0].get("tool", "")
                tool_output = step[1] if isinstance(step[1], str) else str(step[1])

            if not tool_output or tool_output.startswith("MySQL"):
                continue

            try:
                data = json.loads(tool_output)
                if isinstance(data, dict):
                    records = [data]
                elif isinstance(data, list):
                    records = data
                else:
                    continue
            except (json.JSONDecodeError, TypeError):
                continue

            for record in records:
                if not isinstance(record, dict):
                    continue
                if record.get("error"):
                    continue

                obj_id = record.get("object_id", "")
                if not obj_id or obj_id in seen_ids:
                    continue
                seen_ids.add(obj_id)

                detail_url = record.get("detail_url", "")
                image_url = record.get("image_url", "")
                accession = record.get("accession_number", "")
                museum = record.get("museum", "未知博物馆")

                if detail_url or obj_id:
                    sources.append(SourceInfo(
                        museum_name=museum,
                        detail_url=detail_url,
                        object_id=obj_id,
                        image_url=image_url if image_url else None,
                        accession_number=accession if accession else None,
                    ))

        return sources