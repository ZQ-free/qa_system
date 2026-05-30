# 流式对话与 WebSocket 协议

## 1. 流式实现原理

LangGraph 的 `agent.astream()` 是异步迭代器，但每次 `yield` 返回的是整个图的 state snapshot，不包含 LLM 粒度的 token。

因此在 `create_graph_agent(use_streaming=True)` 时，使用 `StreamingChatOpenAI` 子类替代普通 `ChatOpenAI`：

```
StreamingChatOpenAI._stream()
  ↓
for chunk in super()._stream(...):   # 每个 LLM token
      ↓
  if streaming_active:
      token_queue.put(chunk.content)  # 写入队列
  yield chunk                         # 继续返回（LangGraph 正常消费）
```

后台协程 `stream_agent_tokens()` 消费队列，将 token 发给 `token_callback`：

```
LLM _stream() → token_queue
                     ↓
             token_pusher 协程
                     ↓
             token_callback(chunk) → WS 推送 + 累积写入 DB
                     ↓
             done_callback(full)  → WS 发送 done + update_stream_done
```

## 2. WebSocket 端点

```
ws://host/api/qa/ws?session_id={session_id}[&cursor={cursor}]
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `session_id` | 是 | 会话 ID，UUID 格式 |
| `cursor` | 否 | 断点游标，格式 `message_id+sent_offset`，用于续写 |

## 3. 消息协议

### 3.1 服务端 → 客户端

#### 连接确认（`connected`）

连接建立后立即推送，告知客户端当前会话状态：

```json
{
  "type": "connected",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "last_message_id": 124,
  "streaming_done": true,
  "last_content": "完整的 AI 回复内容",
  "sent_offset": 1520
}
```

| 字段 | 说明 |
|------|------|
| `session_id` | 当前会话 ID |
| `last_message_id` | 该会话最后一条消息的数据库 ID（游标基准） |
| `streaming_done` | 最后一条消息是否还在生成中 |
| `last_content` | 最后一条 assistant 消息的完整内容 |
| `sent_offset` | 最后一条消息已发送给客户端的字符偏移量 |

#### 流式 token（`chunk`）

LLM 每输出一个 token 推送一次：

```json
{
  "type": "chunk",
  "message_id": 125,
  "content": "青",
  "done": false
}
```

#### 流式结束（`done`）

LLM 输出完毕时推送，附 cursor 供下次续写：

```json
{
  "type": "done",
  "message_id": 125,
  "content": "青花云龙纹罐现藏于大英博物馆...",
  "cursor": "125+1520"
}
```

#### 续写内容（`resume_remaining`）

客户端重连或发送 `resume` 请求时推送：

```json
{
  "type": "resume_remaining",
  "remaining": "从 offset 开始的剩余内容",
  "done": true
}
```

#### 错误（`error`）

```
{
  "type": "error",
  "message": "具体错误信息"
}
```

#### 心跳响应（`pong`）

```
{
  "type": "pong"
}
```

---

### 3.2 客户端 → 服务端

#### 发送消息（`message`）

```json
{
  "type": "message",
  "content": "青花瓷现在藏在哪里？"
}
```

#### 续写请求（`resume`）

```json
{
  "type": "resume",
  "cursor": "124+1520"
}
```

#### 心跳（`ping`）

```json
{
  "type": "ping"
}
```

## 4. 完整对话时序图

```
客户端                      服务端                      MySQL
  │                           │                           │
  │── WS connect ──────────▶│                           │
  │   session_id=xxx         │                           │
  │                           │── get_last_message() ──▶│
  │                           │◀─────────────────────────│
  │◀─ connected ─────────────│  (streaming_done=TRUE)    │
  │                           │                           │
  │── {"type":"message"...}─▶│                           │
  │                           │── INSERT user msg ─────▶│
  │                           │── INSERT assistant msg ─▶│
  │                           │    (content='', done=FALSE)│
  │                           │                           │
  │                           │ LLM token #1 ──────────▶│ (append chunk)
  │◀─ chunk #1 ─────────────│                           │
  │                           │                           │
  │                           │ LLM token #N ──────────▶│ (append chunk)
  │◀─ chunk #N ─────────────│                           │
  │                           │                           │
  │                           │ LLM done ───────────────▶│ (done=TRUE)
  │◀─ done + cursor ────────│                           │
  │                           │                           │
  │ ... (对话结束，客户端断开) ...                        │
  │                           │                           │
  │── WS reconnect ─────────▶│                           │
  │   session_id=xxx           │                           │
  │                           │── get_last_message() ──▶│
  │                           │◀─────────────────────────│ (done=TRUE)
  │                           │                           │
  │◀─ resume_remaining ──────│ (remaining="", done=TRUE)│
```

## 5. 流式关键参数

| 参数 | 值 | 说明 |
|------|----|------|
| `BUFFER_SIZE` | 20 | 每累积 20 字符批量写入 DB，减少 DB 写入次数 |
| `SESSION_MAX_TURNS` | 5 | 最大历史轮数（可配置） |
| `cursor` 格式 | `{message_id}+{sent_offset}` | 游标由数据库 `id` 和字符偏移量组成 |
| token 推送粒度 | 每 token 一次 WS 推送 | 实时性优先，带宽换实时性 |