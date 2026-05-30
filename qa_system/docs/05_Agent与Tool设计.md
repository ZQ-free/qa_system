# Agent 与 Tool 设计

## 1. Graph Agent 架构

Graph Agent 基于 LangChain 1.x 新 API `langchain.agents.create_agent()` 构建，底层是 LangGraph 的 `CompiledStateGraph`。

### 核心职责

1. 理解用户问题意图
2. 选择合适的 Tool 查询 MySQL / Neo4j
3. 将查询结果转化为自然语言描述
4. 可自我修正重试（Tool 调用失败时尝试其他 Tool）

### 创建流程

```python
# graph_agent.py
def create_graph_agent(use_streaming=False):
    if use_streaming:
        llm = StreamingChatOpenAI(...)  # 劫持 token 流
    else:
        llm = create_llm(temperature=0)

    tools = []
    if settings.ENABLE_MYSQL: tools.extend(MYSQL_TOOLS)   # 9 个
    if settings.ENABLE_NEO4J:  tools.extend(NEO4J_TOOLS)    # 3 个

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=_build_system_prompt(),
    )
    return agent
```

---

## 2. MySQL Tool（ENABLE_MYSQL=on）

共 9 个 Tool，基于 `artifact` 表提供精确的结构化查询。

| Tool | 参数 | 返回 | 用途 |
|------|------|------|------|
| `get_mysql_schema` | 无 | Schema 文本 | 在生成 SQL 前了解表结构 |
| `search_artifacts_by_title` | `keyword: str`, `limit: int=10` | 文物列表 | 模糊搜索文物名称 |
| `search_artifacts_by_artist` | `artist_name: str`, `limit: int=10` | 文物列表 | 按艺术家查作品 |
| `search_artifacts_by_dynasty` | `dynasty: str`, `limit: int=10` | 文物列表 | 按朝代查（兼容中英文） |
| `search_artifacts_by_museum` | `museum_name: str`, `limit: int=10` | 文物列表 | 按博物馆查 |
| `search_artifacts_by_type` | `artifact_type: str`, `limit: int=10` | 文物列表 | 按类型查（Paintings/Ceramics...） |
| `get_artifact_detail` | `object_id: str` | 完整详情 | 含 detail_url（溯源）、dimensions、description |
| `get_artist_bio` | `artist_name: str` | 艺术家信息 | 含 artist_bio、wikipedia_summary、生卒年 |
| `get_similar_artifacts` | `object_id: str`, `limit: int=5` | 相似文物列表 | 按 type 或 dynasty 匹配推荐 |

### 查询策略

- **文物详情类**：先 `search_by_title` 定位 object_id → 再 `get_artifact_detail` 获取完整信息
- **艺术家类**：先 `search_by_artist` 或 `get_artist_bio`
- **推荐类**：先 `search_by_title` 获取 object_id → `get_similar_artifacts`

### Tool 选择指南（注入在 System Prompt）

| 问题类型 | Tool 路径 |
|----------|----------|
| "xxx 藏在哪里？" | search_by_title → get_artifact_detail |
| "xxx 是哪个朝代？" | search_by_title → get_artifact_detail.dynasty |
| "xxx 材质/尺寸？" | search_by_title → get_artifact_detail.material/dimensions |
| "xxx 作者是谁？" | search_by_title → get_artifact_detail.artist |
| "艺术家 xxx 生平？" | get_artist_bio |
| "xxx 还有其他作品？" | search_by_artist |
| "唐代有哪些文物？" | search_by_dynasty("Tang") |
| "推荐 xxx 相关文物" | search_by_title → get_similar_artifacts |

---

## 3. Neo4j Tool（ENABLE_NEO4J=off）

当前未启用，Schema 为假设结构，连接恢复后更新 `NEO4J_SCHEMA_INFO` 即可。

| Tool | 参数 | 返回 | 用途 |
|------|------|------|------|
| `query_neo4j` | `cypher: str`, `params: str=None` | 查询结果 JSON | 执行任意 Cypher 查询 |
| `get_graph_schema` | 无 | Schema 文本 | 了解节点和关系类型 |
| `explore_graph_sample` | `node_label: str` | 样本数据 | 查看某类型节点的实际数据 |

### 假设的图谱 Schema（待连接后更新）

```
节点类型：
- Artifact（文物）：title, type, material, dimensions, description, dynasty
- Museum（博物馆）：name, city, country
- Artist（艺术家）：name, bio, artist_province

关系类型：
- (Artifact)-[:COLLECTED_BY]->(Museum)   文物收藏于博物馆
- (Artifact)-[:CREATED_BY]->(Artist)     文物由艺术家创作
```

---

## 4. System Prompt 设计

Prompt 分为四部分：

### 4.1 Agent 角色与工作流

```
你是一个专门负责海外藏中国文物知识问答的 Agent。
1. 理解用户问题，提取关键实体
2. 根据问题类型选择最合适的 Tool
3. 将查询结果转化为自然语言描述
4. 如果某个 Tool 无结果，尝试其他相关 Tool
```

### 4.2 Tool 使用策略（条件注入）

```python
# 根据 ENABLE_MYSQL / ENABLE_NEO4J 配置动态注入
if not settings.ENABLE_NEO4J:
    prompt += "Neo4j 工具已禁用，请勿调用 Neo4j 相关 Tool"
```

### 4.3 问题类型与 Tool 选择对照表

Markdown 表格，直观展示每类问题应使用的 Tool 组合。

### 4.4 artifact 表字段说明

将真实的 35 列字段说明注入 Prompt，让 Agent 理解每列含义（如 `dynasty` 字段可能包含 `Qing（清）` 的中英文混合格式）。

---

## 5. LangChain Tool 定义规范

所有 Tool 均使用 `@tool` 装饰器：

```python
@tool
async def get_artifact_detail(object_id: str) -> str:
    """
    根据 object_id 查询文物完整详情。

    Args:
        object_id: 文物唯一标识符

    Returns:
        文物完整详情 JSON，含所有字段
    """
    # ... 实现
```

关键要求：
- 每个 Tool 必须有 docstring（LangChain 1.x 要求）
- 异步 `async def` 兼容 LangGraph 的异步迭代
- 返回 JSON 字符串，由 Agent 解析