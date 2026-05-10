"""
main.py — 应用入口
启动 FastAPI 服务，注册所有路由。
运行方式: uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.qa_router import router as qa_router
from config import settings

app = FastAPI(
    title="知识问答子系统",
    description="基于知识图谱与大语言模型的文物问答服务",
    version="1.0.0",
)

# 允许跨域，方便子系统2（Web前端）和子系统4（App）调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 生产环境应改为指定域名
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册问答路由，所有接口都挂在 /api/qa 前缀下
app.include_router(qa_router, prefix="/api/qa")


@app.get("/health")
def health_check():
    """健康检查接口，供其他子系统确认服务是否在线"""
    return {"status": "ok", "mock_mode": settings.MOCK_MODE}
