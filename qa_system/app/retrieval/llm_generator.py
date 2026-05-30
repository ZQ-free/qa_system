"""
app/retrieval/llm_generator.py — 大语言模型调用模块

使用 LangChain ChatOpenAI 对接 OpenAI 兼容协议。
支持任何兼容 OpenAI 协议的模型服务（DeepSeek、通义千问、Ollama、vLLM 等），
只需在 .env 中配置 base_url、api_key、model_name 即可切换。
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from config import settings


def create_llm(
    temperature: float = None,
    max_tokens: int = None,
) -> ChatOpenAI:
    """
    创建 LLM 实例（统一工厂方法）。
    所有模块通过此函数获取 LLM，保持配置一致。
    """
    return ChatOpenAI(
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
        model_name=settings.LLM_MODEL_NAME,
        temperature=temperature if temperature is not None else settings.LLM_TEMPERATURE,
        max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
        timeout=settings.LLM_TIMEOUT,
        max_retries=settings.LLM_MAX_RETRIES,
    )


# ── 意图识别 Prompt ─────────────────────────────────────────────
INTENT_SYSTEM_PROMPT = """你是一个文物知识问答系统的意图识别模块。
你的任务是分析用户的问题，判断它属于以下哪个类别，并只返回对应的JSON。

意图类别说明：
- artifact_location：问文物现在藏在哪个博物馆
- artifact_period：问文物的历史年代或朝代
- artifact_material：问文物的制作材料
- artifact_type：问文物的器物类型分类
- artifact_introduction：请求介绍某件文物的综合信息
- artifact_author：问书画作品的作者
- author_biography：问作者的生平经历
- author_other_works：问某作者还有哪些其他藏品
- dynasty_artifacts：问某朝代有哪些文物
- artifact_dimensions：问文物的尺寸、重量、规格
- artifact_recommend：请求推荐风格或主题相似的文物
- unknown：无法归入以上任何类别

只返回如下格式的JSON，不要有任何其他文字：
{"intent": "意图标签", "entity": "问题中的核心实体名称（文物名/作者名/朝代名）"}

如果无法提取实体，entity填空字符串。"""

# ── 回答生成 Prompt ─────────────────────────────────────────────
ANSWER_SYSTEM_PROMPT = """你是一个专业的中国文物知识问答助手。

你的任务是：根据【知识图谱提供的事实数据】，用流畅自然的中文回答用户的问题。

严格规则（必须遵守）：
1. 只能基于提供的事实数据回答，不能添加任何事实数据中没有的信息
2. 如果事实数据不完整，直接说明"相关数据暂不完整"，不要猜测或补充
3. 回答要简洁，通常2-4句话即可
4. 不要在回答中提及"根据知识图谱"或"根据数据"等系统内部术语
5. 语气专业但亲切，像一个博物馆讲解员

回答格式：直接给出答案，不要有"好的"、"当然"等废话开场。"""


class LLMGenerator:
    """
    大语言模型生成器（LangChain ChatOpenAI 版本）。
    通过 OpenAI 兼容协议对接任意模型服务。
    """

    def __init__(self):
        self.llm = create_llm()

    async def simple_chat(self, system_prompt: str, user_message: str) -> str:
        """
        简单的单轮对话接口，供 IntentParser 调用做意图识别。
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        response = await self.llm.ainvoke(messages)
        return response.content

    async def generate_answer(self, question: str, facts: str, intent: str) -> str:
        """
        根据图谱事实生成最终自然语言回答，供 AnswerBuilder 调用。
        """
        user_message = f"""用户问题：{question}

知识图谱提供的事实数据：
{facts}

请基于以上事实数据回答用户的问题。"""

        messages = [
            SystemMessage(content=ANSWER_SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ]
        response = await self.llm.ainvoke(messages)
        return response.content
