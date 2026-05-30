"""
app/core/sql_memory.py — 短时 SQL 记忆

为 RAG Agent 提供跨轮次的上下文记忆。

设计：
- session_id → List[SQLRecord] 的内存映射
- 每次 RAG 调用 SQL 时记录：query + results
- 下次 RAG 调用时，将历史附加到 context 中
- 内存存储，不持久化
"""

import logging
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class SQLRecord:
    """SQL 执行记录"""
    query: str
    results: str  # JSON 字符串
    result_count: int = 0
    timestamp: int = 0

    def get_summary(self) -> str:
        """生成简洁的摘要"""
        if self.result_count == 0:
            return f"查询无结果: {self.query}"
        return f"查询返回 {self.result_count} 条结果: {self.query}"


class SQLMemory:
    """
    短时 SQL 记忆管理器

    使用示例：
        memory = SQLMemory()
        memory.add_record("session-1", "SELECT * FROM artifact WHERE museum = 'British Museum' LIMIT 10", "[{...}]", 10)
        
        history = memory.get_history("session-1")
        # ['查询返回 10 条结果: SELECT * FROM artifact ...', ...]
    """

    def __init__(self, max_records_per_session: int = 20):
        self._store: dict[str, list[SQLRecord]] = {}
        self._max_records = max_records_per_session

    def add_record(
        self,
        session_id: str,
        query: str,
        results: str,
        result_count: int = 0
    ) -> None:
        """添加一条 SQL 执行记录"""
        if session_id not in self._store:
            self._store[session_id] = []

        import time
        record = SQLRecord(
            query=query,
            results=results,
            result_count=result_count,
            timestamp=int(time.time())
        )

        self._store[session_id].append(record)

        # 限制每个 session 的记录数量
        if len(self._store[session_id]) > self._max_records:
            self._store[session_id] = self._store[session_id][-self._max_records:]

        logging.info(f"[SQLMemory] Added record for session {session_id[:8]}..., total: {len(self._store[session_id])}")

    def get_history(self, session_id: str, max_records: int = 10) -> list[str]:
        """
        获取 SQL 执行历史摘要

        Args:
            session_id: 会话 ID
            max_records: 最多返回的记录数

        Returns:
            历史摘要列表，如：
            [
                "之前查询: SELECT museum, COUNT(*) ... 返回 3 条结果",
                "之前查询: SELECT object_id, title ... 返回 15 条结果",
            ]
        """
        if session_id not in self._store:
            return []

        records = self._store[session_id][-max_records:]
        return [record.get_summary() for record in records]

    def get_full_context(self, session_id: str, max_records: int = 10) -> str:
        """
        获取完整的 SQL 上下文字符串，用于附加到 RAG 消息中
        """
        history = self.get_history(session_id, max_records)
        if not history:
            return ""

        context_lines = ["## 之前的查询记录（供参考）"]
        for i, line in enumerate(history, 1):
            context_lines.append(f"{i}. {line}")

        return "\n".join(context_lines)

    def clear_session(self, session_id: str) -> None:
        """清除指定会话的 SQL 记忆"""
        if session_id in self._store:
            del self._store[session_id]
            logging.info(f"[SQLMemory] Cleared memory for session {session_id[:8]}...")

    def get_record_count(self, session_id: str) -> int:
        """获取指定会话的记录数"""
        return len(self._store.get(session_id, []))


# 全局单例
_sql_memory: Optional[SQLMemory] = None


def get_sql_memory() -> SQLMemory:
    """获取全局 SQLMemory 实例"""
    global _sql_memory
    if _sql_memory is None:
        _sql_memory = SQLMemory()
    return _sql_memory