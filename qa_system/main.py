"""
main.py — 应用入口
启动 FastAPI 服务，注册所有路由。
运行方式: uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.qa_router import router as qa_router
from app.api.ws_router import register_ws_router
from config import settings

app = FastAPI(
    title="知识问答子系统",
    description="基于知识图谱与大语言模型的文物问答服务",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(qa_router, prefix="/api/qa")
register_ws_router(app)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.on_event("shutdown")
async def shutdown():
    from app.db.mysql_client import MySQLClient
    await MySQLClient.close_pool()


@app.get("/")
async def index():
    return FileResponse("app/static/index.html")


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "enable_mysql": settings.ENABLE_MYSQL,
        "enable_neo4j": settings.ENABLE_NEO4J,
    }