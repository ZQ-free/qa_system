# 知识问答子系统 — 测试与启动指南

---

## 目录

- [三个核心文件说明](#三个核心文件说明)
- [环境准备](#环境准备)
- [阶段一：Mock 模式单元测试](#阶段一mock-模式单元测试不依赖任何外部服务)
- [阶段二：Mock 模式启动服务](#阶段二mock-模式启动-http-服务)
- [阶段三：接入 LLM](#阶段三接入-llm)
- [阶段四：联调真实数据库](#阶段四联调真实数据库子系统1就绪后)
- [常见报错处理](#常见报错处理)
- [正常结果判断标准速查](#正常结果判断标准速查)

---

## 三个核心文件说明

| 文件 | 作用 | 什么时候用 |
|------|------|-----------|
| `config.py` | 全局配置中心，管理数据库地址、API密钥、Mock开关等所有参数。其他文件不硬编码任何配置，统一从这里读。 | 每次改配置只改 `.env` 文件，不动代码 |
| `main.py` | HTTP 服务入口，把 FastAPI 应用和路由启动起来，对外暴露接口。运行它就等于"开服"。 | 需要通过浏览器或 HTTP 工具发请求测试时 |
| `test_qa.py` | 自动化单元测试，用 pytest 运行。**不启动服务**，直接在 Python 层面测试各模块逻辑，快速定位问题。 | 每次改完代码后验证有没有破坏已有功能 |

**两种测试方式的区别：**

```
pytest test_qa.py        →  直接测模块逻辑，快，适合开发过程中反复跑
uvicorn main:app + curl  →  测完整 HTTP 链路，慢，适合验收和对接联调
```

---

## 环境准备

**第一步：安装依赖**

```bash
pip install -r requirements.txt
```

**第二步：创建 `.env` 配置文件**

在项目根目录（和 `main.py` 同级）新建 `.env` 文件：

```ini
# Mock 模式开关：true = 用假数据，false = 连真实数据库
MOCK_MODE=true

# Neo4j（Mock模式下这几行不生效，可以先不填）
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# MySQL（Mock模式下不生效）
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=password
MYSQL_DB=artifact_db

# LLM API（Mock模式下不生效，接入LLM时再填）
LLM_PROVIDER=tongyi
LLM_API_KEY=
LLM_MODEL_NAME=qwen-plus
```

> **注意**：`.env` 文件不要提交到 Git，已在 `.gitignore` 中排除。

---

## 阶段一：Mock 模式单元测试（不依赖任何外部服务）

> **适用时机**：开发早期，数据库和 LLM 都还没接入时。随时可以跑。

### 运行方式

```bash
# 在项目根目录下
pytest tests/test_qa.py -v
```

### 测试内容说明

```
TestIntentParser        — 测试意图识别规则是否正确
  test_artifact_location    "青花瓷现在藏在哪个博物馆？" → artifact_location
  test_artifact_period      "这件文物是什么朝代的？"     → artifact_period
  test_artifact_material    "青花罐是什么材质的？"       → artifact_material
  test_author_biography     "夏圭的生平经历是怎样的？"   → author_biography
  test_unknown_intent       "今天天气怎么样？"           → unknown

TestQueryBuilder        — 测试 Cypher 语句是否正确生成
  test_known_intent_returns_query   已知意图应返回包含 MATCH 的 Cypher
  test_unknown_intent_returns_none  UNKNOWN 意图应返回 None
  test_all_intents_have_template    10类意图都必须有对应模板，缺一个就报错

TestMockRetriever       — 测试 Mock 数据返回格式是否符合预期
  test_returns_list               返回值必须是列表
  test_not_found_returns_empty    找不到的实体返回空列表
  test_result_has_required_fields 返回字段必须包含 artifact_name/object_id/detail_url/museum_name
```

### 正常结果

```
tests/test_qa.py::TestIntentParser::test_artifact_location    PASSED
tests/test_qa.py::TestIntentParser::test_artifact_period      PASSED
tests/test_qa.py::TestIntentParser::test_artifact_material    PASSED
tests/test_qa.py::TestIntentParser::test_author_biography     PASSED
tests/test_qa.py::TestIntentParser::test_unknown_intent       PASSED
tests/test_qa.py::TestQueryBuilder::test_known_intent_returns_query    PASSED
tests/test_qa.py::TestQueryBuilder::test_unknown_intent_returns_none   PASSED
tests/test_qa.py::TestQueryBuilder::test_all_intents_have_template     PASSED
tests/test_qa.py::TestMockRetriever::test_returns_list                 PASSED
tests/test_qa.py::TestMockRetriever::test_not_found_returns_empty      PASSED
tests/test_qa.py::TestMockRetriever::test_result_has_required_fields   PASSED

========== 11 passed in X.XXs ==========
```

**只要末尾显示 `N passed, 0 failed` 就算通过。**

---

## 阶段二：Mock 模式启动 HTTP 服务

> **适用时机**：单元测试全通过后，验证完整 HTTP 请求链路，或前端/App子系统来对接接口格式时。

### 启动服务

```bash
# 确认 .env 中 MOCK_MODE=true
uvicorn main:app --reload --port 8000
```

看到以下输出说明启动成功：

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Application startup complete.
```

### 测试方式一：浏览器访问自动文档（推荐）

打开浏览器访问：

```
http://localhost:8000/docs
```

在页面上找到 `POST /api/qa/ask`，点击 `Try it out`，依次发送以下请求：

**测试请求1：正常问题**
```json
{"question": "青花瓷现在藏在哪个博物馆？"}
```

**测试请求2：不存在的文物**
```json
{"question": "这件文物不存在xyz123的材质是什么？"}
```

**测试请求3：无关问题**
```json
{"question": "今天天气怎么样？"}
```

### 测试方式二：命令行 curl

```bash
# 健康检查
curl http://localhost:8000/health

# 正常问题
curl -X POST http://localhost:8000/api/qa/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "青花瓷现在藏在哪个博物馆？"}'

# 不存在的文物
curl -X POST http://localhost:8000/api/qa/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "这件文物不存在xyz123的材质是什么？"}'
```

### 正常结果

**健康检查**应返回：
```json
{"status": "ok", "mock_mode": true}
```

**正常问题**应返回（字段存在且格式正确即可，具体内容是 Mock 假数据）：
```json
{
  "answer_id": "xxxxxxxx",
  "question": "青花瓷现在藏在哪个博物馆？",
  "answer": "文物《青花瓷》现藏于...",
  "intent": "artifact_location",
  "entity": "青花瓷",
  "sources": [
    {
      "museum_name": "...",
      "detail_url": "https://...",
      "object_id": "..."
    }
  ],
  "has_kg_facts": true,
  "has_llm_content": false,
  "not_found": false
}
```

> `has_llm_content` 为 `false` 是正常的，因为 LLM 还没接入，回答直接用图谱事实文本。

**不存在的文物**应返回：
```json
{
  "not_found": true,
  "answer": "抱歉，知识图谱中暂无与该问题相关的数据...",
  "sources": []
}
```

**无关问题**应返回：
```json
{
  "intent": "unknown",
  "not_found": true
}
```

---

## 阶段三：接入 LLM

> **适用时机**：成员C完成 `llm_generator.py` 后。

**第一步**：申请 API Key（推荐通义千问，有免费额度）
- 通义千问：https://dashscope.aliyun.com

**第二步**：修改 `.env`

```ini
MOCK_MODE=true          # 图谱数据仍用 Mock，只是加入 LLM 润色
LLM_API_KEY=sk-xxxxxxxx # 填入真实密钥
LLM_MODEL_NAME=qwen-plus
```

**第三步**：重启服务，发同样的请求

正常结果变化：之前 `answer` 是格式化的事实文本，接入 LLM 后变成自然流畅的语言，且 `has_llm_content` 变为 `true`：

```json
{
  "answer": "青花瓷目前收藏于克利夫兰艺术博物馆，位于美国俄亥俄州克利夫兰市。",
  "has_llm_content": true
}
```

---

## 阶段四：联调真实数据库（子系统1就绪后）

> **适用时机**：子系统1提供了 Neo4j 和 MySQL 连接信息，`schema_agreement.md` 状态更新为已确认。

**第一步**：更新 `.env`

```ini
MOCK_MODE=false
NEO4J_URI=bolt://子系统1的IP:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=子系统1提供的密码
MYSQL_HOST=子系统1的IP
MYSQL_USER=root
MYSQL_PASSWORD=子系统1提供的密码
MYSQL_DB=artifact_db
```

**第二步**：验证数据库连通性

```bash
python -c "
import asyncio
from app.db.neo4j_client import Neo4jClient
result = asyncio.run(Neo4jClient.verify_connectivity())
print('Neo4j 连接:', '成功' if result else '失败')
"
```

**第三步**：用真实文物名提问

用 CSV 数据里实际存在的文物名（如 `Jade Implement`）发请求：

```bash
curl -X POST http://localhost:8000/api/qa/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Jade Implement 现在藏在哪个博物馆？"}'
```

正常结果：`sources` 里的 `object_id` 应与 CSV 里的一致（如 `204498`），`detail_url` 应可以正常访问。

**第四步**：跑完整测试套件

```bash
pytest tests/test_qa.py -v
```

此时测试用的实体名需要换成真实存在于图谱中的文物名，否则会触发 `not_found` 逻辑。

---

## 常见报错处理

| 报错信息 | 原因 | 解决方法 |
|---------|------|---------|
| `ModuleNotFoundError: No module named 'app'` | 没在项目根目录运行 | `cd` 到 `qa_system/` 再运行 |
| `ValidationError: LLM_API_KEY` | `.env` 文件不存在或路径错误 | 确认 `.env` 和 `main.py` 在同一目录 |
| `NotImplementedError: 成员C：请实现...` | LLM 模块未实现但被调用 | 检查 `llm_generator` 初始化，或暂时不传 `llm_client` |
| `ServiceUnavailable: Neo4j` | 数据库连不上 | 确认 `MOCK_MODE=true`，或检查 Neo4j 地址 |
| `11 passed` 但服务启动报错 | 单测通过不代表服务没问题 | 查看 uvicorn 启动日志的具体报错行 |
| JSON 解析错误（意图识别阶段） | LLM 返回了带 markdown 代码块的 JSON | 在 `_parse_by_llm` 里加 `.strip().removeprefix("```json").removesuffix("```")` |

---

## 正常结果判断标准速查

| 阶段 | 关键判断点 |
|------|-----------|
| 单元测试 | 终端末行显示 `N passed, 0 failed` |
| 服务健康检查 | 返回 `{"status":"ok"}` |
| 正常问题 | `not_found=false`，`sources` 非空，有 `detail_url` |
| 不存在的文物 | `not_found=true`，`answer` 含"暂无相关数据" |
| 无关问题 | `intent=unknown`，`not_found=true` |
| LLM 接入后 | `has_llm_content=true`，回答语言更自然 |
| 真实数据库联调 | `object_id` 与 CSV 一致，`detail_url` 可访问 |
