# API 接口设计

所有接口前缀 `/api/qa`。

---

## 1. HTTP REST 接口

### 1.1 创建会话

```
POST /api/qa/session
```

**请求体**：无

**响应** `201 Created`：

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

前端拿到 `session_id` 后在后续请求中传入，即可开启多轮对话。

---

### 1.2 提问（主问答接口）

```
POST /api/qa/ask
```

**请求体**：

```json
{
  "question": "青花瓷现在藏在哪里？",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"   // 可选
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `question` | string | 是 | 用户问题 |
| `session_id` | string | 否 | 有则开启多轮对话，无则单轮 |

**响应** `200 OK`：

```json
{
  "answer_id": "a1b2c3d4",
  "question": "青花瓷现在藏在哪里？",
  "answer": "文物《青花云龙纹罐》现藏于大英博物馆...",
  "intent": "GRAPH_AGENT",
  "entity": "",
  "sources": [
    {
      "museum_name": "British Museum",
      "detail_url": "https://...",
      "object_id": "xxx",
      "image_url": "https://...",
      "accession_number": "xxx"
    }
  ],
  "has_kg_facts": true,
  "has_llm_content": true,
  "not_found": false
}
```

**响应字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `answer_id` | string | 本次回答的唯一 ID |
| `question` | string | 原始问题 |
| `answer` | string | 最终回答（可能经 LLM 润色） |
| `intent` | string | 识别的意图（当前固定为 `GRAPH_AGENT`） |
| `sources` | array | 溯源信息列表，来源博物馆 + 详情页 URL |
| `has_kg_facts` | bool | 是否有图谱/数据库事实 |
| `has_llm_content` | bool | 是否经 LLM 润色 |
| `not_found` | bool | 是否是"暂无相关数据"回答 |

**错误响应** `500 Internal Server Error`：

```json
{
  "detail": "问答服务异常: 具体错误信息"
}
```

---

### 1.3 查询会话历史

```
GET /api/qa/history/{session_id}
```

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `session_id` | string | 会话 ID，UUID 格式 |

**响应** `200 OK`：

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "history": [
    {
      "role": "user",
      "content": "青花瓷现在藏在哪里？",
      "intent": null,
      "entity": null,
      "created_at": "2026-05-29T10:00:00"
    },
    {
      "role": "assistant",
      "content": "文物《青花云龙纹罐》...",
      "intent": "GRAPH_AGENT",
      "entity": "",
      "created_at": "2026-05-29T10:00:01"
    }
  ]
}
```

---

### 1.4 提交反馈

```
POST /api/qa/feedback
```

**请求体**：

```json
{
  "answer_id": "a1b2c3d4",
  "is_helpful": true,
  "comment": "回答准确"   // 可选
}
```

**响应** `200 OK`：

```json
{
  "status": "ok",
  "message": "感谢反馈"
}
```

---

### 1.5 健康检查

```
GET /health
```

**响应** `200 OK`：

```json
{
  "status": "ok",
  "enable_mysql": true,
  "enable_neo4j": false
}
```

---

## 2. WebSocket 接口

### 2.1 建立连接

```
ws://host/api/qa/ws?session_id={session_id}[&cursor={cursor}]
```

| 查询参数 | 必填 | 说明 |
|----------|------|------|
| `session_id` | 是 | 会话 ID |
| `cursor` | 否 | 断点游标，格式 `message_id+sent_offset` |

**连接成功 → 服务端推送 `connected` 事件（见 3.1）**

---

### 2.2 发送消息

客户端 → 服务端：

```json
{
  "type": "message",
  "content": "青花瓷现在藏在哪里？"
}
```

服务端处理后持续推送 `chunk` 事件，流式结束推送 `done`。

---

### 2.3 请求续写

```json
{
  "type": "resume",
  "cursor": "124+1520"
}
```

服务端推送 `resume_remaining` 事件。

---

### 2.4 心跳

```json
{
  "type": "ping"
}
```

服务端响应 `{"type": "pong"}`。

---

## 3. 服务端推送事件

| 事件类型 | 触发时机 | 说明 |
|----------|----------|------|
| `connected` | WS 连接建立 | 连接确认 + 断点检测 |
| `chunk` | LLM 每个 token 输出 | 实时 token 流 |
| `done` | LLM 输出完毕 | 流式结束，附 cursor |
| `resume_remaining` | 重连或 resume 请求 | 推送断点后未接收的内容 |
| `error` | 异常发生时 | 错误信息 |
| `pong` | 收到 ping | 心跳响应 |

---

## 4. 错误码约定

| HTTP 状态码 | 含义 |
|-------------|------|
| 200 | 成功 |
| 201 | 资源创建成功（如 session） |
| 400 | 请求参数错误 |
| 404 | 资源不存在（如 session_id 无对应记录） |
| 500 | 服务端异常（如数据库连接失败、LLM 调用失败） |

---

## 5. CORS 配置

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # 生产环境应限制为具体域名
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 6. 请求示例（curl）

```bash
# 创建会话
curl -X POST http://localhost:8000/api/qa/session

# 提问（单轮）
curl -X POST http://localhost:8000/api/qa/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "青花瓷现在藏在哪里？"}'

# 提问（多轮，带 session_id）
curl -X POST http://localhost:8000/api/qa/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "它的作者是谁？", "session_id": "550e8400-e29b-41d4-a716-446655440000"}'

# 查询历史
curl http://localhost:8000/api/qa/history/550e8400-e29b-41d4-a716-446655440000

# 提交反馈
curl -X POST http://localhost:8000/api/qa/feedback \
  -H "Content-Type: application/json" \
  -d '{"answer_id": "a1b2c3d4", "is_helpful": true}'
```