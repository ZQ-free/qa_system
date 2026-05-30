"""
app/core/session_manager.py — 会话历史管理

职责：
  - 创建新会话（生成 session_id，即 UUID）
  - 按 session_id 查询会话历史（来自 ai_history）
  - 流式写入：append_content 追加 content、update_stream_done 标记完成
  - 流式续写：get_last_message、get_message_by_id
  - 调用 MainQAAgent 处理问答（MainQAAgent 内部调用 Graph Agent）
  - 将 user + assistant 消息写入 ai_history

单条 message 字段：
  - role: user / assistant / system / tool
  - content: 消息正文
  - intent / entity: 意图识别结果（仅 assistant 角色）
  - sources: 溯源信息 JSON（仅 assistant 角色）
  - token_count: 总 token 数（流式结束后更新）
  - sent_offset: 已发送给客户端的字符偏移量（流式续写用）
  - streaming_done: 流式是否已完成（FALSE=正在生成中）
"""

import asyncio
import json
import uuid
from typing import Optional
from config import settings


class SessionManager:
    MAX_TURNS_PER_SESSION = settings.SESSION_MAX_TURNS

    def __init__(self):
        self._main_agent = None

    def _get_main_agent(self):
        if self._main_agent is None:
            from app.agents.main_qa_agent import get_main_qa_agent
            self._main_agent = get_main_qa_agent()
        return self._main_agent

    async def create_session(self) -> dict:
        session_id = str(uuid.uuid4())
        return {"session_id": session_id}

    async def delete_session(self, session_id: str) -> dict:
        from app.db.mysql_client import get_pool
        from app.core.sql_memory import get_sql_memory
        import logging
        logging.info(f"[SessionManager] Deleting session: {session_id}")

        sql_memory = get_sql_memory()
        sql_memory.clear_session(session_id)
        logging.info(f"[SessionManager] Cleared SQL memory for session")

        pool = await get_pool()
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "DELETE FROM ai_history WHERE session_id = %s",
                        (session_id,),
                    )
                    deleted_count = cur.rowcount
                    logging.info(f"[SessionManager] Deleted {deleted_count} messages for session: {session_id}")
                    return {"session_id": session_id, "deleted_count": deleted_count}
        except Exception as e:
            logging.error(f"[SessionManager] Failed to delete session: {e}")
            raise

    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_name: Optional[str] = None,
        tool_input: Optional[dict] = None,
        tool_output: Optional[str] = None,
        intent: Optional[str] = None,
        entity: Optional[str] = None,
    ) -> int:
        from app.db.mysql_client import get_pool

        pool = await get_pool()
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """INSERT INTO ai_history
                           (session_id, role, content, tool_name, tool_input, tool_output,
                            intent, entity, token_count, sent_offset, streaming_done)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, 0, FALSE)""",
                        (
                            session_id, role, content, tool_name,
                            json.dumps(tool_input, ensure_ascii=False) if tool_input else None,
                            tool_output, intent, entity,
                        ),
                    )
                    await conn.commit()
                    await cur.execute("SELECT LAST_INSERT_ID()")
                    row = await cur.fetchone()
                    return row[0] if row else 0
        finally:
            pass

    async def append_content(self, session_id: str, message_id: int, new_chunk: str) -> None:
        from app.db.mysql_client import get_pool

        pool = await get_pool()
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """UPDATE ai_history
                           SET content = CONCAT(IFNULL(content, ''), %s),
                               sent_offset = LENGTH(CONCAT(IFNULL(content, ''), %s))
                           WHERE id = %s AND session_id = %s""",
                        (new_chunk, new_chunk, message_id, session_id),
                    )
                    await conn.commit()
        finally:
            pass

    async def update_stream_done(
        self,
        session_id: str,
        message_id: int,
        total_tokens: int = 0,
    ) -> None:
        from app.db.mysql_client import get_pool

        pool = await get_pool()
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """UPDATE ai_history
                           SET streaming_done = TRUE,
                               token_count = %s,
                               sent_offset = LENGTH(content)
                           WHERE id = %s AND session_id = %s""",
                        (total_tokens, message_id, session_id),
                    )
                    await conn.commit()
        finally:
            pass

    async def get_last_message(self, session_id: str) -> Optional[dict]:
        from app.db.mysql_client import get_pool

        pool = await get_pool()
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """SELECT id, role, content, sent_offset, streaming_done
                           FROM ai_history
                           WHERE session_id = %s
                           ORDER BY created_at DESC, id DESC
                           LIMIT 1""",
                        (session_id,),
                    )
                    row = await cur.fetchone()
                    if not row:
                        return None
                    columns = [c[0] for c in cur.description]
                    return dict(zip(columns, row))
        finally:
            pass

    async def get_message_by_id(self, session_id: str, message_id: int) -> Optional[dict]:
        from app.db.mysql_client import get_pool

        pool = await get_pool()
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """SELECT id, role, content, sent_offset, streaming_done
                           FROM ai_history
                           WHERE id = %s AND session_id = %s""",
                        (message_id, session_id),
                    )
                    row = await cur.fetchone()
                    if not row:
                        return None
                    columns = [c[0] for c in cur.description]
                    return dict(zip(columns, row))
        finally:
            pass

    async def get_history(self, session_id: str, max_turns: Optional[int] = None) -> list[dict]:
        from app.db.mysql_client import get_pool

        limit = (max_turns or self.MAX_TURNS_PER_SESSION) * 2

        pool = await get_pool()
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """SELECT role, content, intent, entity, created_at
                           FROM ai_history
                           WHERE session_id = %s AND role IN ('user', 'assistant')
                           ORDER BY created_at ASC, id ASC
                           LIMIT %s""",
                        (session_id, limit),
                    )
                    rows = await cur.fetchall()
                    columns = [c[0] for c in cur.description]
                    return [dict(zip(columns, row)) for row in rows]
        finally:
            pass

    async def process_with_history(self, question: str, session_id: str) -> dict:
        """
        带会话历史的完整问答流程。
        调用 MainQAAgent.process()，由 MainQAAgent 内部处理：
          1. 从 ai_history 加载历史（已在 session_manager 中获取）
          2. 注入上下文到 Graph Agent
          3. 接收 Graph Agent 的结构化结论
          4. 润色为流畅回答
          5. 将 user + assistant 消息写入 ai_history
        """
        main_agent = self._get_main_agent()
        history = await self.get_history(session_id)

        result = await main_agent.process(
            question=question,
            session_id=session_id,
            chat_history=history,
        )

        polished = await main_agent.generate_polished_answer(
            question=question,
            answer_text=result["answer_text"],
            sources=result["sources"],
        )

        from app.models.schemas import SourceInfo

        sources = [
            SourceInfo(
                museum_name=s.get("museum", "未知博物馆"),
                detail_url=s.get("url", ""),
                object_id=s.get("object_id", ""),
            )
            for s in result["sources"]
        ]

        return {
            "answer": polished,
            "answer_text": result["answer_text"],
            "sources": sources,
            "intent_label": result["intent_label"],
            "user_msg_id": result["user_msg_id"],
            "assistant_msg_id": result["assistant_msg_id"],
        }

    async def process_streaming(
        self,
        question: str,
        session_id: str,
        ws_session_id: str,
        stop_event: Optional[asyncio.Event] = None,
    ) -> int:
        """
        流式问答流程（用于 WebSocket 接口）。

        流程：
          1. 保存 user 消息
          2. 保存空的 assistant 消息（streaming_done=FALSE）
          3. 使用 Main Agent 调用 Graph Agent + 答案润色
          4. token 实时推送 WS；完成后更新数据库
          5. 返回 assistant 消息的 database id（供 cursor 使用）
        """
        from app.core.ws_manager import get_ws_manager
        import logging

        logging.info(f"[SessionManager] process_streaming called for session: {session_id}")

        ws_manager = get_ws_manager()

        await self.save_message(session_id=session_id, role="user", content=question)

        msg_id = await self.save_message(
            session_id=session_id, role="assistant",
            content="", intent="MAIN_AGENT",
        )

        history = await self.get_history(session_id)

        async def agent_step_callback(step_type: str, content: str):
            try:
                await ws_manager.send_agent_step(
                    session_id=ws_session_id,
                    content=content,
                    step_type=step_type,
                )
            except Exception:
                pass

        async def token_callback(token: str):
            nonlocal msg_id
            try:
                await ws_manager.send_chunk(
                    session_id=ws_session_id,
                    message_id=msg_id,
                    chunk=token,
                    done=False,
                )
                await self.append_content(ws_session_id, msg_id, token)
            except Exception:
                pass

        async def done_callback(result: Optional[dict]):
            nonlocal msg_id
            try:
                if result is None:
                    await ws_manager.send_to_session(ws_session_id, {
                        "type": "error",
                        "message": "用户已停止生成",
                    })
                    return

                full_content = result.get("content", "")
                sources = result.get("sources", [])
                intent_label = result.get("intent_label", "UNKNOWN")

                cursor = f"{msg_id}+{len(full_content)}"
                await ws_manager.send_to_session(ws_session_id, {
                    "type": "done",
                    "message_id": msg_id,
                    "content": full_content,
                    "cursor": cursor,
                    "intent": intent_label,
                    "sources": sources,
                })
                await self.update_stream_done(ws_session_id, msg_id)
            except Exception as e:
                logging.error(f"[SessionManager] done_callback error: {e}")
                pass

        try:
            from app.agents.main_agent import run_main_agent
            await run_main_agent(
                question=question,
                history=history,
                token_callback=token_callback,
                done_callback=done_callback,
                session_id=ws_session_id,
                agent_step_callback=agent_step_callback,
                stop_event=stop_event,
            )
        except Exception as e:
            import logging
            logging.error(f"[SessionManager] Error in process_streaming: {e}")
            await ws_manager.send_error(ws_session_id, str(e))

        return msg_id

    async def _flush_chunk(self, session_id: str, message_id: int, chunk: str) -> None:
        try:
            await self.append_content(session_id, message_id, chunk)
        except Exception:
            pass


_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager