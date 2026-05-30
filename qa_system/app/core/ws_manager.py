"""
app/core/ws_manager.py — WebSocket 连接管理器

职责：
- 管理 session_id → WebSocket 客户端的映射（支持多端登录同一会话）
- 广播消息到所有连接同一 session 的客户端
- 支持客户端断线重连后从游标处继续接收
- 线程安全

WebSocket 消息协议（服务端 → 客户端）：

  1. 建立连接时，服务端推送连接确认：
     {
       "type": "connected",
       "session_id": "xxx",
       "last_message_id": 123,
       "streaming_done": true/false
     }

  2. 中间消息（不持久化，可折叠显示）：
      {
        "type": "agent_step",
        "content": "正在调用数据库查询...",
        "step_type": "reasoning" | "tool_call" | "tool_result"
      }
      {
        "type": "tool_call",
        "tool_name": "execute_sql",
        "tool_args": "SELECT museum...",
        "done": false
      }
      {
        "type": "tool_result",
        "tool_name": "execute_sql",
        "result": "[{...}]",
        "done": false
      }

  3. 最终回复（流式输出，持久化）：
     {
       "type": "chunk",
       "message_id": 124,
       "content": "这是刚刚生成的 token...",
       "done": false
     }

  4. 流式结束：
     {
       "type": "done",
       "message_id": 124,
       "content": "完整的 AI 回复全文",
       "cursor": "124+1520"
     }

  5. 错误：
     {
       "type": "error",
       "message": "具体错误信息"
     }

客户端 → 服务端：

  1. 发送消息：
     {"type": "message", "content": "用户的问题"}

  2. 请求续写：
     {"type": "resume", "cursor": "124+1520"}

  3. 停止生成：
     {"type": "stop"}

  4. 心跳：
     {"type": "ping"}
"""

import asyncio
import json
from typing import Optional
from fastapi import WebSocket
import weakref


class WSClient:
    def __init__(self, websocket: WebSocket, session_id: str):
        self.websocket = websocket
        self.session_id = session_id


class WSManager:
    _instance: Optional["WSManager"] = None

    def __init__(self):
        self._connections: dict[str, list[WSClient]] = {}
        self._lock = asyncio.Lock()
        self._notifier_events: dict[str, asyncio.Event] = {}

    @classmethod
    def get_instance(cls) -> "WSManager":
        if cls._instance is None:
            cls._instance = WSManager()
        return cls._instance

    async def connect(self, websocket: WebSocket, session_id: str) -> dict:
        """
        客户端 WS 连接时调用。

        返回连接确认信息，包含最后一条消息的游标状态，
        供客户端判断是否需要续写。
        """
        await websocket.accept()

        async with self._lock:
            if session_id not in self._connections:
                self._connections[session_id] = []
                self._notifier_events[session_id] = asyncio.Event()

            self._connections[session_id].append(WSClient(websocket, session_id))

        from app.core.session_manager import get_session_manager
        sm = get_session_manager()
        last_record = await sm.get_last_message(session_id)

        return {
            "type": "connected",
            "session_id": session_id,
            "last_message_id": last_record["id"] if last_record else None,
            "streaming_done": last_record["streaming_done"] if last_record else True,
            "last_content": last_record["content"] if last_record else "",
            "sent_offset": last_record["sent_offset"] if last_record else 0,
        }

    async def disconnect(self, websocket: WebSocket, session_id: str) -> None:
        async with self._lock:
            if session_id in self._connections:
                self._connections[session_id] = [
                    c for c in self._connections[session_id]
                    if c.websocket != websocket
                ]
                if not self._connections[session_id]:
                    del self._connections[session_id]

    def _get_clients(self, session_id: str) -> list[WSClient]:
        return self._connections.get(session_id, [])

    async def send_to_session(self, session_id: str, payload: dict) -> None:
        """向所有连接该 session 的客户端广播消息。"""
        clients = self._get_clients(session_id)
        for client in clients:
            try:
                await client.websocket.send_json(payload)
            except Exception:
                pass

    async def send_chunk(
        self,
        session_id: str,
        message_id: int,
        chunk: str,
        done: bool,
        cursor: Optional[str] = None,
        full_content: Optional[str] = None,
    ) -> None:
        """发送流式 chunk 或最终完成消息。"""
        if done:
            await self.send_to_session(session_id, {
                "type": "done",
                "message_id": message_id,
                "content": full_content or "",
                "cursor": cursor or "",
            })
        else:
            await self.send_to_session(session_id, {
                "type": "chunk",
                "message_id": message_id,
                "content": chunk,
                "done": False,
            })

    async def send_error(self, session_id: str, message: str) -> None:
        await self.send_to_session(session_id, {
            "type": "error",
            "message": message,
        })

    async def send_agent_step(
        self,
        session_id: str,
        content: str,
        step_type: str = "reasoning"
    ) -> None:
        await self.send_to_session(session_id, {
            "type": "agent_step",
            "content": content,
            "step_type": step_type,
        })

    async def send_tool_call(self, session_id: str, tool_name: str, tool_args: str) -> None:
        await self.send_to_session(session_id, {
            "type": "tool_call",
            "tool_name": tool_name,
            "tool_args": tool_args,
        })

    async def send_tool_result(self, session_id: str, tool_name: str, result: str) -> None:
        await self.send_to_session(session_id, {
            "type": "tool_result",
            "tool_name": tool_name,
            "result": result[:500] if len(result) > 500 else result,
        })

    async def resume_stream(
        self,
        session_id: str,
        cursor: str,
    ) -> dict:
        """
        客户端传入 cursor 续写请求。
        cursor 格式："message_id+sent_offset"
        返回从断点起的剩余内容（可能为空）。
        """
        try:
            msg_id_str, offset_str = cursor.rsplit("+", 1)
            msg_id = int(msg_id_str)
            offset = int(offset_str)
        except (ValueError, IndexError):
            return {"error": "无效的 cursor 格式"}

        from app.core.session_manager import get_session_manager
        sm = get_session_manager()
        record = await sm.get_message_by_id(session_id, msg_id)

        if not record:
            return {"error": f"未找到 message_id={msg_id} 的记录"}

        full_content = record["content"] or ""
        if offset >= len(full_content):
            return {"remaining": "", "done": True, "cursor": cursor}

        remaining = full_content[offset:]
        done = record["streaming_done"]

        return {
            "remaining": remaining,
            "done": done,
            "cursor": f"{msg_id}+{offset + len(remaining)}",
        }

    @property
    def active_sessions(self) -> list[str]:
        return list(self._connections.keys())


_ws_manager: Optional[WSManager] = None


def get_ws_manager() -> WSManager:
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WSManager.get_instance()
    return _ws_manager