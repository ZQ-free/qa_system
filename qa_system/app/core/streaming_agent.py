"""
app/core/streaming_agent.py — 流式 Graph Agent

通过劫持 ChatOpenAI 的流式输出，实现 LLM token 粒度的实时推送。

原理：
1. 创建一个 StreamingChatOpenAI 子类，在 stream() 时将每个 token chunk
   写入一个异步队列
2. 在 agent.astream 迭代过程中，消费该队列的 token，发给 WS 推送回调
3. agent.astream 结束后（done_callback），发送完成信号并更新数据库

关键优势：
- LangGraph 的 astream 本身支持流式，每次 chunk 包含完整的 graph state
- 通过 StreamingChatOpenAI 劫持底层的 _stream 方法，可以获取每个 LLM token
- 不需要修改 graph_agent.py 或 create_agent()，仅在此模块中包装
"""

import asyncio
from typing import Callable, Optional, Any
from langchain_openai import ChatOpenAI
from langchain_core.outputs import ChatGenerationChunk


class StreamingChatOpenAI(ChatOpenAI):
    """
    ChatOpenAI 的流式子类。

    与普通 ChatOpenAI 的区别：
    - stream() 和 astream() 会将每个 token 写入 self._token_queue (asyncio.Queue)
    - 调用 start_streaming() 启动队列消费；stop_streaming() 关闭
    - 适用于在 agent.astream 迭代过程中劫持 LLM token 的场景
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._token_queue: asyncio.Queue[str] = asyncio.Queue()
        self._streaming_active = False
        self._full_text = ""

    def start_streaming(self) -> None:
        self._streaming_active = True
        self._token_queue = asyncio.Queue()
        self._full_text = ""

    def stop_streaming(self) -> None:
        self._streaming_active = False

    def get_token_queue(self) -> asyncio.Queue:
        return self._token_queue

    def get_full_text(self) -> str:
        return self._full_text

    def _stream(
        self,
        messages: list,
        stop: Optional[list] = None,
        **kwargs: Any,
    ):
        for chunk in super()._stream(messages, stop=stop, **kwargs):
            if self._streaming_active:
                text = chunk.content or ""
                if text:
                    self._full_text += text
                    try:
                        self._token_queue.put_nowait(text)
                    except asyncio.QueueFull:
                        pass
            yield chunk


async def stream_agent_tokens(
    agent,
    messages: list,
    token_callback: Callable[[str], None],
    done_callback: Callable[[str], None],
) -> None:
    """
    异步迭代 agent.astream，将 LLM token 实时推送给 callback。

    实现方式：
    1. 启动一个后台协程持续消费 LLM 的 asyncio.Queue
    2. 迭代 agent.astream（拿到 graph state chunks）
    3. 后台协程将 token 发给 token_callback
    4. astream 结束后调用 done_callback
    """
    llm = agent.nodes.get("model")
    streaming_llm = None

    if llm is not None and hasattr(llm, "_model"):
        candidate = llm._model
        if isinstance(candidate, StreamingChatOpenAI):
            streaming_llm = candidate

    if streaming_llm:
        streaming_llm.start_streaming()

    async def _token_pusher():
        if not streaming_llm:
            done_callback("")
            return

        q = streaming_llm.get_token_queue()
        try:
            while True:
                try:
                    token = await asyncio.wait_for(q.get(), timeout=0.05)
                    token_callback(token)
                except asyncio.TimeoutError:
                    if not streaming_llm._streaming_active:
                        break
                    continue
            full = streaming_llm.get_full_text()
            done_callback(full)
        finally:
            streaming_llm.stop_streaming()

    pusher_task = asyncio.create_task(_token_pusher())

    try:
        async for _ in agent.astream({"messages": messages}):
            pass
    finally:
        if streaming_llm:
            streaming_llm.stop_streaming()
        try:
            await asyncio.wait_for(pusher_task, timeout=1.0)
        except asyncio.TimeoutError:
            pusher_task.cancel()
            try:
                await pusher_task
            except asyncio.CancelledError:
                pass