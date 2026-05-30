"""
config.py — 全局配置
读取 .env 文件中的所有配置项，整个项目统一从这里导入。
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── 数据库 Tool 开关 ──────────────────────────────────────
    ENABLE_MYSQL: bool = True
    ENABLE_NEO4J: bool = False

    # ── Neo4j 图数据库 ────────────────────────────────────────
    NEO4J_URI: str = "bolt://10.4.70.168:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password123"

    # ── MySQL 关系型数据库 ─────────────────────────────────────
    MYSQL_HOST: str = "47.96.152.190"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "!software2303"
    MYSQL_DB: str = "overseas_chinese_artifacts"

    # ── 大语言模型（OpenAI 兼容协议）─────────────────────────
    # 支持任何兼容 OpenAI 协议的服务：
    #   - OpenAI:       base_url=https://api.openai.com/v1
    #   - DeepSeek:     base_url=https://api.deepseek.com/v1
    #   - 通义千问:     base_url=https://dashscope.aliyuncs.com/compatible-mode/v1
    #   - 智谱GLM:      base_url=https://open.bigmodel.cn/api/paas/v4
    #   - Ollama本地:   base_url=http://localhost:11434/v1
    #   - vLLM:         base_url=http://localhost:8000/v1
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL_NAME: str = "deepseek-chat"

    # ── LLM 生成参数 ──────────────────────────────────────────
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 2048
    LLM_TIMEOUT: int = 60
    LLM_MAX_RETRIES: int = 2

    # ── 会话配置（多轮对话）───────────────────────────────────
    SESSION_MAX_TURNS: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()