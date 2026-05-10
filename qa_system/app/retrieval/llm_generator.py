"""
app/retrieval/llm_generator.py — 大语言模型调用模块
【负责人：成员C】

职责：
  1. 封装大模型 API 调用（通义千问 / 智谱GLM / OpenAI 可切换）
  2. 提供两个对外接口：
     - simple_chat()：供 IntentParser 做意图识别
     - generate_answer()：供 AnswerBuilder 润色最终答案
  3. 严格限制 LLM 的行为：只能润色语言，不能添加图谱中没有的事实

对应课设要求：
  "将检索结果作为上下文传入大语言模型，生成自然流畅的回答"
  "对于由大语言模型生成的补充性描述，须与知识图谱事实性内容明确区分标注"
  "有效避免大模型幻觉问题"
"""

from config import settings
from app.core.intent_types import Intent


# ── 回答生成的 System Prompt ─────────────────────────────────────────────
# 关键约束：只能基于给定事实回答，不能凭空添加内容
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
    大语言模型生成器。
    
    【成员C的工作】：
    1. 选择一个 LLM API（推荐通义千问，有免费额度）
    2. 实现 _call_api() 方法，完成真实的 HTTP 请求
    3. simple_chat() 和 generate_answer() 的框架已搭好，只需实现底层调用
    
    API 申请地址：
    - 通义千问：https://dashscope.aliyun.com （阿里云，推荐）
    - 智谱GLM：https://open.bigmodel.cn
    - 不推荐 OpenAI（国内访问不稳定）
    """

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL_NAME

        # 懒加载 LangChain 客户端（只在真正调用时初始化）
        self._client = None

    def _get_client(self):
        """
        【成员C实现】初始化 LangChain 客户端。
        
        通义千问示例：
          from langchain_community.llms import Tongyi
          return Tongyi(dashscope_api_key=self.api_key, model_name=self.model)
        
        智谱GLM示例：
          from langchain_community.chat_models import ChatZhipuAI
          return ChatZhipuAI(api_key=self.api_key, model=self.model)
        """
        if self._client is None:
            # TODO: 成员C实现
            # 示例（通义千问）：
            # from langchain_community.llms import Tongyi
            # self._client = Tongyi(dashscope_api_key=self.api_key)
            pass
        return self._client

    async def simple_chat(self, system_prompt: str, user_message: str) -> str:
        """
        简单的单轮对话接口，供 IntentParser 调用做意图识别。
        
        输入：system_prompt（任务说明）+ user_message（用户问题）
        输出：模型的文本回复
        
        【成员C实现】
        """
        # TODO: 成员C实现
        # 示例（LangChain通用调用方式）：
        # from langchain_core.messages import SystemMessage, HumanMessage
        # client = self._get_client()
        # messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_message)]
        # response = await client.ainvoke(messages)
        # return response.content
        raise NotImplementedError("成员C：请实现 simple_chat()")

    async def generate_answer(self, question: str, facts: str, intent: str) -> str:
        """
        根据图谱事实生成最终自然语言回答，供 AnswerBuilder 调用。
        
        facts: 图谱查询结果格式化后的文本，作为 LLM 的上下文
        
        关键：LLM 只能基于 facts 中的内容回答，框架通过 Prompt 约束这一点。
        
        【成员C实现】
        """
        user_message = f"""用户问题：{question}

知识图谱提供的事实数据：
{facts}

请基于以上事实数据回答用户的问题。"""

        # TODO: 成员C实现
        # return await self.simple_chat(ANSWER_SYSTEM_PROMPT, user_message)
        raise NotImplementedError("成员C：请实现 generate_answer()")
