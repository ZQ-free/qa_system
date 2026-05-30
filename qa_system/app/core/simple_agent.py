"""
app/core/simple_agent.py — 简化的流式 Agent

直接使用 OpenAI SDK 实现工具调用，无需 LangChain。

流程：
1. 接收用户问题
2. 调用 LLM（带工具定义），LLM 可能返回：
   - tool_calls: 需要执行工具
   - content: 最终回答
3. 如果是 tool_calls，执行工具并把结果发回给 LLM
4. 如果是 content，流式输出到 WebSocket
"""

import json
import asyncio
from typing import Callable, Optional, Any
from openai import AsyncOpenAI
from config import settings
from app.agents.tools.mysql_tool import (
    get_mysql_schema,
    search_artifacts_by_title,
    search_artifacts_by_artist,
    search_artifacts_by_dynasty,
    search_artifacts_by_museum,
    search_artifacts_by_type,
    get_artifact_detail,
    get_artist_bio,
    get_similar_artifacts,
)


MYSQL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_mysql_schema",
            "description": "获取 MySQL 数据库表结构信息。在生成 SQL 查询之前调用此工具了解表结构和字段。",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_artifacts_by_title",
            "description": "根据文物名称关键词模糊搜索文物列表。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "搜索关键词"},
                    "limit": {"type": "integer", "description": "返回数量上限", "default": 10}
                },
                "required": ["keyword"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_artifacts_by_artist",
            "description": "根据创作者姓名搜索文物列表。",
            "parameters": {
                "type": "object",
                "properties": {
                    "artist_name": {"type": "string", "description": "艺术家姓名"},
                    "limit": {"type": "integer", "description": "返回数量上限", "default": 10}
                },
                "required": ["artist_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_artifacts_by_dynasty",
            "description": "根据朝代搜索文物列表。",
            "parameters": {
                "type": "object",
                "properties": {
                    "dynasty": {"type": "string", "description": "朝代名称"},
                    "limit": {"type": "integer", "description": "返回数量上限", "default": 10}
                },
                "required": ["dynasty"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_artifacts_by_museum",
            "description": "根据博物馆名称搜索文物列表。",
            "parameters": {
                "type": "object",
                "properties": {
                    "museum_name": {"type": "string", "description": "博物馆名称"},
                    "limit": {"type": "integer", "description": "返回数量上限", "default": 10}
                },
                "required": ["museum_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_artifacts_by_type",
            "description": "根据文物类型搜索文物列表。常见类型：Paintings, Ceramics, Sculptures, Prints, Textiles, Bronzes 等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_type": {"type": "string", "description": "文物类型"},
                    "limit": {"type": "integer", "description": "返回数量上限", "default": 10}
                },
                "required": ["artifact_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_artifact_detail",
            "description": "根据 object_id 查询文物的完整详情信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "object_id": {"type": "string", "description": "文物唯一标识符"}
                },
                "required": ["object_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_artist_bio",
            "description": "根据艺术家姓名查询其详细信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "artist_name": {"type": "string", "description": "艺术家姓名"}
                },
                "required": ["artist_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_similar_artifacts",
            "description": "查询与指定文物相似的其他文物。",
            "parameters": {
                "type": "object",
                "properties": {
                    "object_id": {"type": "string", "description": "参考文物 object_id"},
                    "limit": {"type": "integer", "description": "返回数量", "default": 5}
                },
                "required": ["object_id"]
            }
        }
    },
]


SYSTEM_PROMPT = """你是一个专门负责海外藏中国文物知识问答的AI助手。

你的职责是接收用户问题，通过工具查询数据库，返回结构化结论。

## 数据库信息
MySQL 数据库（overseas_chinese_artifacts.artifact）存储了约7000件海外藏中国文物的信息。

## 工作流程
1. 理解用户问题
2. 使用工具查询数据库获取相关信息
3. 根据查询结果直接回答用户问题

## 工具使用
你可以使用以下工具来查询数据库：
- search_artifacts_by_title: 按文物名称搜索
- search_artifacts_by_artist: 按艺术家搜索
- search_artifacts_by_dynasty: 按朝代搜索（如 Qing、Tang、Han）
- search_artifacts_by_museum: 按博物馆搜索
- search_artifacts_by_type: 按类型搜索
- get_artifact_detail: 获取文物详情
- get_artist_bio: 获取艺术家信息
- get_similar_artifacts: 获取相似文物

## 回答要求
- 直接回答问题，不要说"根据查询结果"等过渡语
- 如有溯源信息（detail_url），在回答末尾附上
- 如数据库无相关数据，直接告知用户
- 保持回答简洁、准确
"""


async def execute_tool(tool_name: str, arguments: dict) -> str:
    """执行工具并返回结果"""
    try:
        if tool_name == "get_mysql_schema":
            return await get_mysql_schema()
        elif tool_name == "search_artifacts_by_title":
            return await search_artifacts_by_title(
                keyword=arguments.get("keyword", ""),
                limit=arguments.get("limit", 10)
            )
        elif tool_name == "search_artifacts_by_artist":
            return await search_artifacts_by_artist(
                artist_name=arguments.get("artist_name", ""),
                limit=arguments.get("limit", 10)
            )
        elif tool_name == "search_artifacts_by_dynasty":
            return await search_artifacts_by_dynasty(
                dynasty=arguments.get("dynasty", ""),
                limit=arguments.get("limit", 10)
            )
        elif tool_name == "search_artifacts_by_museum":
            return await search_artifacts_by_museum(
                museum_name=arguments.get("museum_name", ""),
                limit=arguments.get("limit", 10)
            )
        elif tool_name == "search_artifacts_by_type":
            return await search_artifacts_by_type(
                artifact_type=arguments.get("artifact_type", ""),
                limit=arguments.get("limit", 10)
            )
        elif tool_name == "get_artifact_detail":
            return await get_artifact_detail(
                object_id=arguments.get("object_id", "")
            )
        elif tool_name == "get_artist_bio":
            return await get_artist_bio(
                artist_name=arguments.get("artist_name", "")
            )
        elif tool_name == "get_similar_artifacts":
            return await get_similar_artifacts(
                object_id=arguments.get("object_id", ""),
                limit=arguments.get("limit", 5)
            )
        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
    except Exception as e:
        return json.dumps({"error": f"Tool execution failed: {str(e)}"})


async def run_simple_agent(
    question: str,
    history: list,
    token_callback: Callable[[str], None],
    done_callback: Callable[[str, list], None],
) -> None:
    """
    运行简化的流式 Agent。

    Args:
        question: 用户问题
        history: 对话历史
        token_callback: 流式 token 回调
        done_callback: 完成回调，传入 (answer_text, sources)
    """
    import logging
    logging.info(f"[SimpleAgent] Processing question: {question[:50]}...")

    client = AsyncOpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        timeout=settings.LLM_TIMEOUT,
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for h in history:
        role = "user" if h.get("role") == "user" else "assistant"
        messages.append({"role": role, "content": h.get("content", "")})

    messages.append({"role": "user", "content": question})

    full_response = ""
    sources = []
    max_tool_calls = 10
    tool_call_count = 0

    while tool_call_count < max_tool_calls:
        tool_call_count += 1

        try:
            stream = await client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=messages,
                tools=MYSQL_TOOLS if tool_call_count <= 5 else [],
                stream=True,
                temperature=settings.LLM_TEMPERATURE,
            )
        except Exception as e:
            logging.error(f"[SimpleAgent] API call failed: {e}")
            break

        assistant_message = ""
        tool_calls = []
        current_tool_call = None

        try:
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta is None:
                    continue
                if delta.content:
                    assistant_message += delta.content
                    await token_callback(delta.content)
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        if tc.function and tc.function.name:
                            current_tool_call = {
                                "id": tc.id or f"call_{len(tool_calls)}",
                                "name": tc.function.name,
                                "arguments": ""
                            }
                            tool_calls.append(current_tool_call)
                        elif current_tool_call and tc.function and tc.function.arguments:
                            current_tool_call["arguments"] += tc.function.arguments
        except Exception as e:
            logging.error(f"[SimpleAgent] Stream iteration failed: {e}")
            break

        if not assistant_message and not tool_calls:
            break

        if tool_calls:
            messages.append({"role": "assistant", "content": assistant_message})

            for tc in tool_calls:
                try:
                    args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                except json.JSONDecodeError:
                    args = {}

                logging.info(f"[SimpleAgent] Calling tool: {tc['name']}")
                result = await execute_tool(tc["name"], args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result
                })

                try:
                    result_data = json.loads(result)
                    if isinstance(result_data, list) and len(result_data) > 0:
                        for item in result_data:
                            if isinstance(item, dict) and item.get("detail_url"):
                                sources.append({
                                    "museum": item.get("museum", "未知博物馆"),
                                    "url": item.get("detail_url", ""),
                                    "object_id": item.get("object_id", "")
                                })
                    elif isinstance(result_data, dict) and result_data.get("detail_url"):
                        sources.append({
                            "museum": result_data.get("museum", "未知博物馆"),
                            "url": result_data.get("detail_url", ""),
                            "object_id": result_data.get("object_id", "")
                        })
                except:
                    pass

        elif assistant_message:
            full_response = assistant_message
            messages.append({"role": "assistant", "content": assistant_message})
            break
        else:
            break

    if not full_response and tool_call_count >= max_tool_calls:
        full_response = "抱歉，问题较为复杂，请在简化后重试。"

    await done_callback(full_response, sources)