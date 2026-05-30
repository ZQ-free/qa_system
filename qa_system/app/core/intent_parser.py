"""
app/core/intent_parser.py — 意图识别模块
【负责人：成员A】

职责：判断用户输入的问题属于10类意图中的哪一类。
选择调用大模型-api
实现方式：将问题发给LLM，通过精心设计的 Prompt 让模型返回意图标签。

输入：用户问题字符串
输出：Intent 类中定义的意图常量字符串

课设对应要求：
  支持10类简单问答，每类对应一个意图标签。
  对于无法识别的问题，返回 Intent.UNKNOWN。
"""

import json
from app.core.intent_types import Intent
from app.retrieval.llm_generator import INTENT_SYSTEM_PROMPT


class IntentParser:
    """
    意图识别器。
    
    需要实现 parse() 方法，其余框架已搭好。
    建议先实现基于关键词的简单版本，再升级为LLM版本。
    """

    def __init__(self, llm_client=None):
        """
        llm_client: 由成员C实现的 LLMGenerator 实例，用于调用大模型。
                    如果为 None，则使用关键词规则作为降级方案。
        """
        self.llm_client = llm_client

    async def parse(self, question: str) -> dict:
        """
        识别问题的意图和核心实体。
        
        返回示例：
          {"intent": "artifact_location", "entity": "青花瓷"}
          {"intent": "unknown", "entity": ""}
        
        【成员A的实现要点】：
        1. 先调用 _parse_by_llm()（需要LLM客户端）
        2. 如果LLM不可用，降级到 _parse_by_rules()
        3. 无论哪种方式，保证返回格式一致
        """
        if self.llm_client:
            return await self._parse_by_llm(question)
        return self._parse_by_rules(question)

    async def _parse_by_llm(self, question: str) -> dict:
        """
        用 LLM 识别意图。
        
        调用 self.llm_client.simple_chat() 发送 INTENT_SYSTEM_PROMPT + 用户问题，
        解析返回的JSON，提取 intent 和 entity 字段。
        
        LLM 解析失败时自动降级到规则版识别。
        """
        try:
            response = await self.llm_client.simple_chat(
                system_prompt=INTENT_SYSTEM_PROMPT,
                user_message=question,
            )
            response = response.strip()
            if response.startswith("```"):
                response = response.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            result = json.loads(response)

            if result.get("intent") not in Intent.all_known():
                result["intent"] = Intent.UNKNOWN
            if "entity" not in result:
                result["entity"] = ""

            return result
        except (json.JSONDecodeError, KeyError, Exception) as e:
            print(f"[IntentParser LLM错误] {e}，降级到规则识别")
            return self._parse_by_rules(question)

    def _parse_by_rules(self, question: str) -> dict:
        """
        需要实现：基于关键词的规则识别（降级方案，开发早期使用）。
        
        不需要LLM即可运行，适合最开始联调时验证整体流程。（如果大语言模型无法使用才考虑用这个）
        精度较低，但能保证10类基本问题都能被识别到。
        """
        q = question.lower()

        # 规则顺序很重要，越具体的规则越靠前
        if any(w in q for w in ["藏于", "收藏", "哪家博物馆", "在哪里", "哪个博物馆"]):
            return self._extract_entity(question, Intent.ARTIFACT_LOCATION)

        if any(w in q for w in ["朝代", "年代", "时期", "什么时候", "哪个朝代"]):
            return self._extract_entity(question, Intent.ARTIFACT_PERIOD)

        if any(w in q for w in ["材质", "材料", "什么做", "由什么"]):
            return self._extract_entity(question, Intent.ARTIFACT_MATERIAL)

        if any(w in q for w in ["类型", "类别", "什么器", "器物"]):
            return self._extract_entity(question, Intent.ARTIFACT_TYPE)

        if any(w in q for w in ["作者", "谁画", "谁写", "谁创作"]):
            return self._extract_entity(question, Intent.ARTIFACT_AUTHOR)

        if any(w in q for w in ["生平", "经历", "简介", "是谁"]):
            return self._extract_entity(question, Intent.AUTHOR_BIOGRAPHY)

        if any(w in q for w in ["还有哪些作品", "其他作品", "同一作者"]):
            return self._extract_entity(question, Intent.AUTHOR_OTHER_WORKS)

        if any(w in q for w in ["哪些文物", "代表文物", "朝的文物"]):
            return self._extract_entity(question, Intent.DYNASTY_ARTIFACTS)

        if any(w in q for w in ["尺寸", "重量", "大小", "多高", "多重"]):
            return self._extract_entity(question, Intent.ARTIFACT_DIMENSIONS)

        if any(w in q for w in ["介绍", "是什么", "告诉我"]):
            return self._extract_entity(question, Intent.ARTIFACT_INTRODUCTION)

        return {"intent": Intent.UNKNOWN, "entity": ""}

    def _extract_entity(self, question: str, intent: str) -> dict:
        """
        从问题中提取实体名称（简单版：去掉疑问词和动词后剩余的名词短语）。
        
        需要优化：这里只是粗糙实现，LLM版本会更准确。
        """
        # 需要去掉的疑问词和功能词
        stop_words = [
            "这件文物", "该文物", "这幅", "这个", "请", "介绍", "一下",
            "现在", "目前", "是", "的", "吗", "呢", "啊", "？", "?",
            "哪家博物馆", "藏于", "收藏", "在哪里", "属于", "哪个", "朝代",
            "材质", "材料", "由什么", "作者", "谁画", "生平", "尺寸"
        ]
        entity = question
        for word in stop_words:
            entity = entity.replace(word, "")
        entity = entity.strip()

        return {"intent": intent, "entity": entity}
