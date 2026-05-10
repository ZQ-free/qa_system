"""
app/api/qa_router.py — 接口层（API Layer）

职责：只做三件事——接收请求、调用核心处理层、返回响应。
不包含任何业务逻辑。

对外暴露的接口（供子系统2 Web端 和 子系统4 App调用）：
  POST /api/qa/ask        — 提问，获取回答
  POST /api/qa/feedback   — 提交回答质量反馈
"""

import uuid
from fastapi import APIRouter, HTTPException

from app.models.schemas import AskRequest, AskResponse, FeedbackRequest
from app.core.qa_engine import QAEngine

router = APIRouter()

# QAEngine 是整个问答流程的总调度，接口层只调用它
qa_engine = QAEngine()


@router.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    """
    主问答接口。
    
    流程：
      1. 接收用户问题
      2. 交给 QAEngine 处理（意图识别→实体抽取→图谱查询→LLM生成→组装答案）
      3. 返回带溯源信息的标准化响应
    
    调用示例（供子系统2/4参考）：
      POST /api/qa/ask
      {"question": "青花瓷现在藏在哪里？"}
    """
    try:
        result = await qa_engine.process(
            question=request.question,
            session_id=request.session_id,
        )
        return result
    except Exception as e:
        # 统一错误处理，不把内部异常暴露给调用方
        raise HTTPException(status_code=500, detail=f"问答服务异常: {str(e)}")


@router.post("/feedback")
async def feedback(request: FeedbackRequest):
    """
    反馈接口。用户标记回答是否准确。
    对应课设"答案溯源"中的可信度机制，以及选做的"问答质量反馈机制"。
    
    当前必做阶段只记录日志，后续选做时可接入数据库存储。
    """
    # TODO（选做）：将反馈写入数据库，供后台管理子系统查询
    print(f"[反馈] answer_id={request.answer_id}, helpful={request.is_helpful}")
    return {"status": "ok", "message": "感谢反馈"}
