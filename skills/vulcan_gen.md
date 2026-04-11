---
name: vulcan-fin-if-gen
description: Create Vulcan platform tasks for Chinese Financial IF Benchmark. Generates input JSONL, pre/post-processing handlers for constraint selection, track generation, response generation, and evaluation scoring tasks.
---

# Vulcan 金融 IF Benchmark 任务生成器

基于 Vulcan 单轮任务平台，为中文金融指令遵循 Benchmark 生成数据。Vulcan 架构：

```
输入 JSONL → 前处理 handler → 模型 API 调用 → 后处理 handler → 输出 JSONL
```

- 单轮任务，每行独立执行，无跨行状态
- 前/后处理签名：`def handler(data)`
- `data.input`：输入行 JSON 字符串
- `data.steps["model_request"].output`：模型返回 JSON 字符串
- metadata 字段透传，不发给模型

## 项目上下文

### 约束池

63 条约束，分 4 类：GH(20) + GS(9) + FH(10) + FS(24)
- Hard (GH/FH)：rule-based checker 验证，binary 1/0
- Soft (GS/FS)：LLM-as-a-judge 验证，binary 1/0
- 权威表：`docs/constraint_reference_table.csv`
- 约束含参数占位符如 `{N}`, `{目标受众}`, `{指定内容}`，需 LLM 按 query 语义填充

### Query 池

502 条 query（`data/query_pool/query_pool_v3.json`），来源：
- FinEval 原题 113 条
- FIFE 模板 142 条
- DISC-FIN-SFT 152 条
- WritingBench Finance 95 条

### 3 种 Track

| Track | 约束来源 | 评测方式 |
|-------|---------|---------|
| hard_track | 仅 GH + FH 约束 | rule checker |
| soft_track | 仅 GS + FS 约束 | LLM judge |
| mixed_track | GH/FH + GS/FS 混合 | rule + LLM |

每种 track 下按约束数量分层（1 / 2 / 3 / 4-5 个约束）。

### 评分体系

全部 binary 1/0，两级指标：
- **constraint-level**：每个约束是否满足（1/0）
- **instruction-level**：一条 instruction 的所有约束是否全部满足（全 1 才算 1，否则 0）

### 互斥约束对

组合时不可同时出现：
- FN-7（术语缩写给全称） vs FS-10（避免专业术语）
- GH-7（使用表格） vs GH-18（禁止表格）
- GH-6（使用列表） vs GH-19（禁止列表）
- FH-8（禁百分号） vs FS-4（引用具体财务指标数据）
- FH-9（禁阿拉伯数字） vs FS-4/FS-5

---

## 任务 1：Track 生成（LLM 选约束 + 参数化）

用强模型（Claude Opus / GPT-4o）为每个 query 选择合适的约束并参数化。

**输入数据**：每行一个 query，附带约束池全文供 LLM 选择
```json
{
  "messages": [
    {"role": "system", "content": "你是中文金融IF Benchmark的数据构造专家..."},
    {"role": "user", "content": "为以下query选择合适的约束并参数化...\n\nQuery: ...\n\n约束池: ..."}
  ],
  "query_id": "DISC_0001",
  "query_text": "...",
  "track_type": "hard_track",
  "n_constraints": 2
}
```

**前处理**：
```python
def handler(data):
    import json
    input_data = json.loads(data.input)

    system_content = None
    messages = []
    for msg in input_data["messages"]:
        if msg["role"] == "system":
            system_content = msg["content"]
        else:
            messages.append(msg)

    result = {
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 4096,
    }

    if system_content:
        result["system"] = system_content

    return result
```
- 低 temperature (0.3) 保证约束选择的稳定性
- 需要 system prompt，必须提取到顶层

**后处理**：
```python
def handler(data):
    import json
    input_data = json.loads(data.input)
    model_output = json.loads(data.steps["model_request"].output)

    llm_text = ""
    if "content" in model_output:
        for block in model_output["content"]:
            if block.get("type") == "text":
                llm_text = block.get("text", "")
                break

    if not llm_text:
        llm_text = model_output.get("output", [{}])[0].get("content", [{}])[0].get("text", "")

    # 解析 JSON
    constraints = []
    success = False
    try:
        # 处理 markdown 代码块
        text = llm_text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        parsed = json.loads(text)
        constraints = parsed.get("constraints", [])
        success = True
    except (json.JSONDecodeError, TypeError):
        pass

    return {
        "query_id": input_data.get("query_id"),
        "track_type": input_data.get("track_type"),
        "n_constraints": input_data.get("n_constraints"),
        "constraints": constraints,
        "success": success,
        "raw_response": llm_text[:2000],
    }
```

---

## 任务 2：Response 生成（被评测模型回答）

用被评测模型对 track（query + 约束组合）生成回答。

**输入数据**：
```json
{
  "messages": [
    {"role": "user", "content": "组合后的完整 prompt（query + 约束）"}
  ],
  "sample_id": "DISC_0001_hard_2_001",
  "query_id": "DISC_0001",
  "track_type": "hard_track",
  "constraints": [...]
}
```

**前处理**：
```python
def handler(data):
    import json
    input_data = json.loads(data.input)

    result = {
        "messages": input_data["messages"],
        "temperature": 0.7,
        "max_tokens": 16000,
    }

    return result
```
- 无 system prompt
- 标准生成参数

**后处理**：
```python
def handler(data):
    import json
    input_data = json.loads(data.input)
    model_output = json.loads(data.steps["model_request"].output)

    llm_text = ""
    if "content" in model_output:
        for block in model_output["content"]:
            if block.get("type") == "text":
                llm_text = block.get("text", "")
                break

    if not llm_text:
        llm_text = model_output.get("output", [{}])[0].get("content", [{}])[0].get("text", "")

    # 去 thinking 标签
    marker = "</think>\n\n"
    pos = llm_text.find(marker)
    if pos != -1:
        llm_text = llm_text[pos + len(marker):]

    return {
        "sample_id": input_data.get("sample_id"),
        "query_id": input_data.get("query_id"),
        "track_type": input_data.get("track_type"),
        "constraints": input_data.get("constraints"),
        "response": llm_text,
    }
```

---

## 任务 3：Soft Constraint 评分（LLM Judge）

用 judge 模型对 soft constraint 逐条评分。

**输入数据**：每行一个 (response, constraint) 评分请求
```json
{
  "messages": [
    {"role": "system", "content": "你是一个严格的约束遵循评测器..."},
    {"role": "user", "content": "## Constraint Meta\n...\n## Rubric\n...\n## Query\n...\n## Candidate Answer\n..."}
  ],
  "sample_id": "DISC_0001_soft_2_001",
  "constraint_id": "GS-3",
  "constraint_text": "使用正式书面语，不得口语化"
}
```

**前处理**：
```python
def handler(data):
    import json
    input_data = json.loads(data.input)

    system_content = None
    messages = []
    for msg in input_data["messages"]:
        if msg["role"] == "system":
            system_content = msg["content"]
        else:
            messages.append(msg)

    result = {
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 1024,
    }

    if system_content:
        result["system"] = system_content

    return result
```
- 低 temperature (0.1) 保证评分稳定
- judge 不开 thinking

**后处理**：
```python
def handler(data):
    import json
    input_data = json.loads(data.input)
    model_output = json.loads(data.steps["model_request"].output)

    llm_text = ""
    if "content" in model_output:
        for block in model_output["content"]:
            if block.get("type") == "text":
                llm_text = block.get("text", "")
                break

    if not llm_text:
        llm_text = model_output.get("output", [{}])[0].get("content", [{}])[0].get("text", "")

    score = None
    passed = None
    reason = ""
    success = False
    try:
        text = llm_text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        parsed = json.loads(text)
        if "score" in parsed:
            score = int(parsed["score"])
            if score in [0, 1]:
                passed = (score == 1)
                reason = parsed.get("reason", "")
                success = True
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    return {
        "sample_id": input_data.get("sample_id"),
        "constraint_id": input_data.get("constraint_id"),
        "constraint_text": input_data.get("constraint_text", ""),
        "score": score,
        "passed": passed,
        "reason": reason,
        "success": success,
        "raw_response": llm_text[:500],
    }
```

---

## 关键文件位置

| 文件 | 路径 |
|------|------|
| Query 池 | `data/query_pool/query_pool_v3.json` |
| 约束池 CSV | `docs/constraint_reference_table.csv` |
| 约束池文档 | `docs/constraint_pool.md` |
| Hard checker | `verifier/rules/*.py` |
| Soft rubric | `verifier/rubrics/*.md` |
| Rubric runner | `verifier/rubric_runner.py` |
| 评分主脚本 | `scripts/score_responses.py` |

## 注意事项

1. Track 生成用强模型（Claude Opus / GPT-4o），temperature=0.3
2. Response 生成用被评测模型，标准参数
3. Soft 评分用 judge 模型，temperature=0.1，不开 thinking
4. Hard 约束不需要 Vulcan 任务，本地 rule checker 直接跑
5. 评分全部 binary 1/0，半对算 0
6. 互斥约束对不可同时出现在同一 track 中
