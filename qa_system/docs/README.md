# 设计文档索引

本文档目录包含知识问答子系统的完整设计说明。

---

## 文档列表

| 序号 | 文件 | 内容 |
|------|------|------|
| 01 | [系统架构](./01_系统架构.md) | 整体架构图、技术栈、配置开关、核心模块职责、数据流 |
| 02 | [数据库设计](./02_数据库设计.md) | artifact 表结构（35列）、ai_history 表结构（含流式字段） |
| 03 | [会话与历史管理](./03_会话与历史管理.md) | session 生命周期、history 存储策略、cursor 续写机制 |
| 04 | [流式对话与 WebSocket 协议](./04_流式对话与WebSocket协议.md) | token 劫持原理、WS 消息协议、完整时序图 |
| 05 | [Agent 与 Tool 设计](./05_Agent与Tool设计.md) | Graph Agent 架构、MySQL 9个Tool、Neo4j 3个Tool、System Prompt |
| 06 | [API 接口设计](./06_API接口设计.md) | REST 接口 + WebSocket 接口详细说明、错误码、curl 示例 |

---

## 快速导航

### 开发人员

- **了解系统全貌** → [01 系统架构](./01_系统架构.md)
- **理解数据模型** → [02 数据库设计](./02_数据库设计.md)
- **理解接口协议** → [06 API 接口设计](./06_API接口设计.md)

### 前端开发

- **集成 HTTP 接口** → [06 API 接口设计 - REST 部分](./06_API接口设计.md)
- **集成 WebSocket** → [04 流式对话与 WebSocket 协议](./04_流式对话与WebSocket协议.md)
- **理解续写机制** → [03 会话与历史管理 - 断线重连](./03_会话与历史管理.md)

### 后端开发

- **新增 Tool** → [05 Agent 与 Tool 设计 - MySQL Tool 部分](./05_Agent与Tool设计.md)
- **修改流式逻辑** → [04 流式对话与 WebSocket 协议](./04_流式对话与WebSocket协议.md)
- **修改会话管理** → [03 会话与历史管理](./03_会话与历史管理.md)

---

## 关键文件路径

```
qa_system/
├── .env                           # 配置开关（ENABLE_MYSQL, ENABLE_NEO4J）
├── config.py                      # 配置读取
├── main.py                        # FastAPI 入口
├── docs/                          # 本文档目录
│   ├── 01_系统架构.md
│   ├── 02_数据库设计.md
│   ├── 03_会话与历史管理.md
│   ├── 04_流式对话与WebSocket协议.md
│   ├── 05_Agent与Tool设计.md
│   └── 06_API接口设计.md
└── app/
    ├── api/
    │   ├── qa_router.py           # HTTP REST 路由
    │   └── ws_router.py           # WebSocket 路由
    ├── core/
    │   ├── qa_engine.py          # 问答引擎调度
    │   ├── session_manager.py     # 会话与历史管理
    │   ├── ws_manager.py          # WebSocket 连接管理
    │   ├── streaming_agent.py     # 流式 LLM token 劫持
    │   ├── answer_builder.py      # 答案组装 + 溯源
    │   ├── intent_parser.py       # 意图识别（备用）
    │   └── query_builder.py       # 查询构建（备用）
    ├── agents/
    │   ├── graph_agent.py         # Graph Agent 创建
    │   └── tools/
    │       ├── mysql_tool.py     # 9 个 MySQL Tool
    │       └── neo4j_tool.py      # 3 个 Neo4j Tool
    ├── db/
    │   └── mysql_client.py        # MySQL 连接池
    └── retrieval/
        └── llm_generator.py      # LLM 工厂函数（OpenAI 兼容）
```