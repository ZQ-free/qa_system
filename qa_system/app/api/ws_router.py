"""
app/api/ws_router.py — WebSocket 路由

连接方式：ws://host/api/qa/ws?session_id=xxx
（可选）&cursor=124+1520  断点续写时传入

消息协议：
  客户端 → 服务端：
    {"type": "message", "content": "用户的问题"}
    {"type": "resume", "cursor": "124+1520"}
    {"type": "stop"}           # 停止当前生成
    {"type": "ping"}

  服务端 → 客户端：
    {"type": "connected", "session_id": "...", "last_message_id": ..., "streaming_done": true/false}
    {"type": "chunk", "message_id": 124, "content": "token...", "done": false}
    {"type": "done", "message_id": 124, "content": "完整回复", "cursor": "124+1520", "intent": "...", "sources": [...]}
    {"type": "error", "message": "错误信息"}
    {"type": "resume_remaining", "remaining": "...", "done": true/false}
"""

import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect, Query
from app.core.ws_manager import get_ws_manager
from app.core.session_manager import get_session_manager


def register_ws_router(app):
    @app.websocket("/api/qa/ws")
    async def websocket_endpoint(
        websocket: WebSocket,
        session_id: str = Query(..., description="会话 ID"),
        cursor: str = Query(None, description="断点游标，格式：message_id+sent_offset"),
    ):
        ws_manager = get_ws_manager()
        sm = get_session_manager()
        stop_event = asyncio.Event()
        current_task = None

        conn_info = await ws_manager.connect(websocket, session_id)
        await websocket.send_json(conn_info)

        if cursor:
            resume_result = await ws_manager.resume_stream(session_id, cursor)
            if "error" not in resume_result:
                await websocket.send_json({
                    "type": "resume_remaining",
                    "remaining": resume_result.get("remaining", ""),
                    "done": resume_result.get("done", True),
                    "cursor": f"{cursor.rsplit('+', 1)[0]}+{resume_result.get('cursor', cursor)}",
                })
            else:
                await websocket.send_json({"type": "error", "message": resume_result["error"]})
        else:
            last_record = conn_info
            if not last_record.get("streaming_done", True):
                last_msg_id = last_record.get("last_message_id")
                last_content = last_record.get("last_content", "")
                last_offset = last_record.get("sent_offset", 0)
                if last_msg_id and last_offset < len(last_content):
                    await websocket.send_json({
                        "type": "resume_remaining",
                        "remaining": last_content[last_offset:],
                        "done": False,
                        "cursor": f"{last_msg_id}+{len(last_content)}",
                    })

        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "message": "无效的 JSON"})
                    continue

                msg_type = msg.get("type", "")

                if msg_type == "message":
                    if current_task and not current_task.done():
                        stop_event.set()
                        try:
                            await current_task
                        except:
                            pass

                    stop_event = asyncio.Event()
                    question = msg.get("content", "").strip()
                    if not question:
                        continue

                    import logging
                    logging.info(f"[WS] Received message: {question[:50]}...")

                    current_task = asyncio.create_task(
                        sm.process_streaming(
                            question=question,
                            session_id=session_id,
                            ws_session_id=session_id,
                            stop_event=stop_event,
                        )
                    )

                elif msg_type == "stop":
                    import logging
                    logging.info("[WS] Received stop signal")
                    stop_event.set()

                elif msg_type == "resume":
                    cursor_val = msg.get("cursor", "")
                    if cursor_val:
                        resume_result = await ws_manager.resume_stream(session_id, cursor_val)
                        if "error" in resume_result:
                            await websocket.send_json({"type": "error", "message": resume_result["error"]})
                        else:
                            await websocket.send_json({
                                "type": "resume_remaining",
                                "remaining": resume_result.get("remaining", ""),
                                "done": resume_result.get("done", True),
                                "cursor": resume_result.get("cursor", ""),
                            })

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

        except WebSocketDisconnect:
            pass
        except Exception as e:
            await ws_manager.send_error(session_id, str(e))
        finally:
            stop_event.set()
            await ws_manager.disconnect(websocket, session_id)