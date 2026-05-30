# 海外藏中国文物知识问答系统

基于知识图谱与大语言模型的文物问答服务，支持流式对话、多轮会话和 RAG 检索。

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Vue 3)                       │
│  ┌─────────┐  ┌────────────┐  ┌───────────────────┐   │
│  │ Sidebar │  │ MessageList│  │   ChatInput       │   │
│  └─────────┘  └────────────┘  └───────────────────┘   │
└───────────────────────┬───────────────────────────────────┘
                        │ WebSocket / HTTP
┌───────────────────────▼───────────────────────────────────┐
│                    Backend (FastAPI)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ ws_router  │  │ qa_router   │  │  Main Agent     │  │
│  └──────┬─────┘  └──────┬──────┘  └────────┬────────┘  │
│         │                 │                   │            │
│  ┌──────▼───────────────▼───────────────────▼────────┐   │
│  │              Graph Agent                          │   │
│  │  ┌──────────────┐    ┌─────────────────────┐   │   │
│  │  │ SQLMemory    │    │ execute_sql Tool   │   │   │
│  │  │ (短时记忆)   │    │ (Text-to-SQL)      │   │   │
│  │  └──────────────┘    └─────────────────────┘   │   │
│  └─────────────────────────────────────────────────┘   │
│                        │                                 │
│  ┌─────────────────────▼─────────────────────────────┐   │
│  │                 MySQL (Artifact)                 │   │
│  └─────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────┘
```

## 核心组件

### Agent 架构（双 Agent 设计）

| Agent | 职责 | 文件 |
|-------|------|------|
| **Graph Agent** | 意图识别 + SQL 查询 + RAG 总结 | `app/agents/graph_agent.py` |
| **Main Agent** | 答案润色 + 流式输出 | `app/agents/main_agent.py` |

### 短时记忆 (SQLMemory)

- **位置**: `app/core/sql_memory.py`
- **用途**: 跨轮次的 SQL 查询上下文，解决指代问题（如"这些文物"）
- **特性**: 内存存储，不持久化

### WebSocket 消息协议

**服务端 → 客户端**:
```json
{ "type": "connected", "session_id": "xxx" }
{ "type": "chunk", "message_id": 1, "content": "token..." }
{ "type": "done", "message_id": 1, "content": "完整回复" }
{ "type": "agent_step", "step_type": "tool_call", "content": "正在调用..." }
```

**客户端 → 服务端**:
```json
{ "type": "message", "content": "用户问题" }
{ "type": "stop" }
{ "type": "ping" }
```

## 目录结构

```
qa_system/
├── app/
│   ├── agents/               # Agent 实现
│   │   ├── graph_agent.py    # Graph Agent (RAG)
│   │   ├── main_agent.py     # Main Agent (润色)
│   │   └── tools/
│   │       └── mysql_tool.py # SQL 执行工具
│   ├── api/                  # API 路由
│   │   ├── qa_router.py     # REST API
│   │   └── ws_router.py      # WebSocket 路由
│   ├── core/                  # 核心逻辑
│   │   ├── session_manager.py # 会话管理
│   │   ├── sql_memory.py     # 短时 SQL 记忆
│   │   └── ws_manager.py    # WebSocket 管理
│   └── db/                   # 数据库客户端
├── chat-web/                  # 前端 (Vue 3)
│   └── src/
│       ├── api/chat.ts       # API 调用
│       ├── components/        # Vue 组件
│       └── stores/chat.ts     # Pinia 状态
├── docs/                      # 设计文档
└── Makefile                   # 启动脚本
```

## 快速启动

### 方式一：本地开发

```bash
# 安装依赖
make install-venv

# 启动服务（后端 8000，前端 5173）
make run

# 查看状态
make status

# 查看日志
make logs

# 停止服务
make stop
```

### 方式二：Docker 部署

```bash
# 复制环境变量文件
cp qa_system/.env.example .env
# 编辑 .env 配置 LLM 和数据库

# 构建并启动
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

服务地址：
- 后端 API: http://localhost:8000
- 健康检查: http://localhost:8000/health

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/qa/session` | 创建会话 |
| DELETE | `/api/qa/session/{id}` | 删除会话 |
| GET | `/api/qa/history/{id}` | 查询历史 |
| WS | `/api/qa/ws?session_id=xxx` | 流式对话 |

## 环境变量

```bash
# LLM 配置
LLM_BASE_URL=https://api.example.com
LLM_API_KEY=your-key
LLM_MODEL_NAME=model-name

# 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=xxx
MYSQL_DB=overseas_chinese_artifacts
```

## 开发指南

### 添加新工具

1. 在 `app/agents/tools/mysql_tool.py` 中实现函数
2. 在 `app/agents/graph_agent.py` 的 `MYSQL_TOOLS` 中注册
3. 在 `SYSTEM_PROMPT` 中添加说明

### 修改消息类型

1. 前端类型: `chat-web/src/types/index.ts`
2. 后端 WS 消息: `app/core/ws_manager.py`
3. 前端处理逻辑: `chat-web/src/stores/chat.ts`

### 调试日志

后端日志前缀:
- `[GraphAgent]` - Graph Agent 执行日志
- `[MainAgent]` - Main Agent 执行日志
- `[MySQL]` - SQL 执行日志
- `[SQLMemory]` - 短时记忆日志

查看实时日志:
```bash
tail -f qa_system/.backend.log
```
