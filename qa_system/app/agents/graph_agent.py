"""
app/agents/graph_agent.py — Graph Agent（意图识别 + 工具调用 + 结果总结）

职责：
1. 接收用户问题
2. 调用 execute_sql 查询数据库
3. 调用 summarize_result 工具输出查询结果的自然语言总结
4. 返回总结作为 RAG context 给 Main Agent
"""

import json
import asyncio
from typing import Callable, Optional
from openai import AsyncOpenAI
from config import settings
from app.agents.tools.mysql_tool import execute_sql


MYSQL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_sql",
            "description": "执行安全的 SQL SELECT 查询。只允许 SELECT，必须包含 LIMIT（最大100行）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL 查询语句"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_result",
            "description": "将 SQL 查询结果转换为自然语言总结，作为 RAG context 返回。",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "查询结果的自然语言总结"
                    }
                },
                "required": ["summary"]
            }
        }
    },
]


SYSTEM_PROMPT = """你是一个专门负责海外藏中国文物知识问答的"查询 Agent"。

你的职责：
1. 接收用户问题
2. 分析是否需要查询数据库
3. 如果需要，生成 SQL 并调用 execute_sql 查询
4. 查询完成后，调用 summarize_result 输出自然语言总结

## 数据库信息
- overseas_chinese_artifacts.artifact 表（6997条记录）
- 字段：object_id, title, artist, dynasty, type, museum, location, detail_url 等

## SQL 规则
1. 必须以 SELECT 开头
2. 必须包含 LIMIT（最大100行）
3. 支持模糊匹配：WHERE column LIKE '%关键词%'
4. 支持聚合：COUNT, GROUP BY

## 输出要求
调用 summarize_result 工具输出查询结果的自然语言总结，例如：
"查询到大英博物馆包含 156 件中国文物，包括绘画、陶瓷等类型。"

重要：summarize_result 的输出将作为 RAG context 传给 Main Agent。
"""


async def run_graph_agent(
    question: str,
    on_thinking: Optional[Callable[[str], None]] = None,
    on_tool_call: Optional[Callable[[str, str], None]] = None,
    on_tool_result: Optional[Callable[[str, str], None]] = None,
    stop_event: Optional[asyncio.Event] = None,
) -> dict:
    import logging
    logging.info(f"[GraphAgent] Processing: {question[:50]}...")
    logging.info(f"[GraphAgent] === Starting Graph Agent ===")

    if stop_event is None:
        stop_event = asyncio.Event()

    client = AsyncOpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        timeout=settings.LLM_TIMEOUT,
    )

    logging.info(f"[GraphAgent] Model: {settings.LLM_MODEL_NAME}")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question}
    ]
    logging.info(f"[GraphAgent] Messages prepared")

    max_turns = 10
    rag_context = ""

    for turn in range(max_turns):
        logging.info(f"[GraphAgent] --- Turn {turn + 1}/{max_turns} ---")
        if stop_event.is_set():
            logging.info("[GraphAgent] Stopped")
            break

        try:
            logging.info(f"[GraphAgent] Calling LLM...")
            stream = await client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=messages,
                tools=MYSQL_TOOLS,
                stream=True,
                temperature=0,
            )
        except Exception as e:
            logging.error(f"[GraphAgent] LLM call failed: {e}")
            return {
                "rag_context": "",
                "intent_label": "ERROR"
            }

        tool_calls = []
        current_tc = None
        finish_reason = None

        try:
            async for chunk in stream:
                if stop_event.is_set():
                    break
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                finish_reason = chunk.choices[0].finish_reason

                if delta is None:
                    continue

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        if tc.function and tc.function.name:
                            logging.info(f"[GraphAgent] LLM requests tool: {tc.function.name}")
                            current_tc = {
                                "id": tc.id or f"call_{len(tool_calls)}",
                                "name": tc.function.name,
                                "arguments": ""
                            }
                            tool_calls.append(current_tc)
                        elif current_tc and tc.function and tc.function.arguments:
                            current_tc["arguments"] += tc.function.arguments
        except Exception as e:
            logging.error(f"[GraphAgent] Stream failed: {e}")
            break

        logging.info(f"[GraphAgent] finish_reason: {finish_reason}, tool_calls: {len(tool_calls)}")

        if finish_reason == "stop":
            break

        if tool_calls:
            logging.info(f"[GraphAgent] Processing {len(tool_calls)} tool calls")

            assistant_msg = {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"]}
                    }
                    for tc in tool_calls
                ]
            }
            messages.append(assistant_msg)

            for tc in tool_calls:
                args = {}
                try:
                    if tc["arguments"]:
                        args = json.loads(tc["arguments"])
                except:
                    pass

                logging.info(f"[GraphAgent] Executing tool: {tc['name']}")

                if on_tool_call:
                    await on_tool_call(tc["name"], json.dumps(args))

                if tc["name"] == "execute_sql":
                    query = args.get("query", "")
                    result = await execute_sql(query)
                    logging.info(f"[GraphAgent] execute_sql result: {len(result)} chars")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result
                    })
                    if on_tool_result:
                        await on_tool_result(tc["name"], result)

                elif tc["name"] == "summarize_result":
                    summary = args.get("summary", "")
                    rag_context = summary
                    logging.info(f"[GraphAgent] summarize_result: {summary[:100]}...")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": summary
                    })
                    if on_tool_result:
                        await on_tool_result(tc["name"], summary)
                else:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": f"Unknown tool: {tc['name']}"
                    })
        else:
            logging.info("[GraphAgent] No tool calls, finishing")
            break

    logging.info(f"[GraphAgent] === Finished ===")
    logging.info(f"[GraphAgent] rag_context: {len(rag_context)} chars")

    return {
        "rag_context": rag_context,
        "intent_label": "ARTIFACT_QUERY"
    }