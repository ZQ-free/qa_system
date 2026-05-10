"""
config.py — 全局配置
读取 .env 文件中的所有配置项，整个项目统一从这里导入。
切换 Mock 模式只需修改 .env 中的 MOCK_MODE=true/false。
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── 运行模式 ──────────────────────────────────────────────
    # True = 使用 Mock 数据（子系统1未完成时使用）
    # False = 连接真实 Neo4j 和 MySQL
    MOCK_MODE: bool = True

    # ── Neo4j 图数据库（子系统1提供） ─────────────────────────
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # ── MySQL 关系型数据库（子系统1提供） ─────────────────────
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "password"
    MYSQL_DB: str = "artifact_db"

    # ── 大语言模型 API ────────────────────────────────────────
    # 推荐使用通义千问（DASHSCOPE）或智谱GLM
    LLM_PROVIDER: str = "tongyi"          # 可选: tongyi / zhipu / openai
    LLM_API_KEY: str = ""                 # 在 .env 中填入真实密钥
    LLM_MODEL_NAME: str = "qwen-plus"     # 通义千问模型名

    # ── 会话配置（多轮对话，选做预留） ───────────────────────
    SESSION_MAX_TURNS: int = 5            # 保留最近几轮对话上下文

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
