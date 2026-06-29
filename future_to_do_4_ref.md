# Future TODO: Context Sourcing 重构

> 待实施。先理清逻辑，统一动手时再执行。

---

## 1  现状问题

### 1.1 Context 质量：摘要而非原文

现在 raw_contexts/ 里的真实法规文档（SEC/FINRA/FDIC 等）进 prompt 时被压缩成了摘要级内容：

- FINRA Rule 2090: 92KB 原文 → 3.9KB（4.3%），还带 HTML 导航残渣
- Apple 10-Q: 1.5MB → 4–6KB summary，有些只有 594 chars 纯数字摘要
- 与真实工作场景有 gap：分析师面对的是原始文档，不是别人替他总结好的摘要

### 1.2 Doc 数量：强制 2–4 个

当前每条 prompt 固定塞 2–4 份 source doc（2 doc: 17%, 3 doc: 78%, 4 doc: 5%）。但很多 task 天然只需要 1 份文档（一份 10-Q 做 earnings review，一份 loan application 做 intake）。200–400 chars 的合成 policy/scenario doc 信息密度低，有凑数嫌疑。

### 1.3 Context 复用率

- Test 307 条 → 304 个 unique context 组合（99% 独一无二）
- Train 621 条 → 478 个 unique context 组合（93% 独一无二）
- 少数被复用的是公共法规（FINRA 2090 被 16 条引用），作为通用评判依据反复出现是合理的

---

## 2  改进方案

### 2.1 原文片段替代摘要

- 从 raw doc 中抽取**连续原文段落**（verbatim excerpt），不改写、不总结
- 按段落/章节的自然边界切割，保持语义完整（不从句子中间截断）
- 例：从 Apple 10-Q 抽 Revenue Discussion 整段，而非截取第 3–47 行
- 目标片段长度：**2000–5000 tokens**（比现在 500 chars 摘要长很多，但远不至于整篇文档）

### 2.2 按 task 需求决定 doc 数量

- **单文档 task**（自然只需要 1 份）：
  - Earnings review ← 1 份 10-Q/10-K 片段
  - Loan application intake ← 1 份 SBA Form
  - Risk disclosure review ← 1 份 Risk Factors 章节
  - Financial statement analysis ← 1 份 financial statements 片段
  - AML red-flag review ← 1 份 alert/advisory

- **多文档 task**（天然需要交叉参考）：
  - KYC onboarding ← 客户资料 + CDD 规则（2 份）
  - Suitability review ← 客户 profile + 产品说明 + 适当性规则（2–3 份）
  - Covenant check ← 贷款协议 + 合规政策（2 份）
  - Trade order ticket ← 交易指令 + 控制标准（2 份）

- 不再强制最低 2 doc

### 2.3 成本控制

- Prompt 均长预计从 ~4700 chars 涨到 ~8000–12000 chars，成本约翻 2–3 倍
- Bench 307 条 + Train ~600 条，数据集不大，总 API 成本可控
- 不是 agent 场景，不存在多轮调用放大问题

---

## 3  论文收益

1. **"verbatim excerpts from public regulatory filings"** — 比 "summaries" 更客观，reviewer 无法质疑摘要质量
2. **prompt length 作为 contribution**：FinIF prompts avg X tokens, 10× longer than IFEval，体现 document-grounded 的真实复杂度
3. **自然实现 source-disjoint**：同一文档的不同段落可分给 train/test，从根源消除泄漏质疑

---

## 4  实施步骤

1. **改 `ingest_external_contexts.py`**：按段落/章节边界做 sliding-window verbatim excerpt，去掉 HTML 导航残渣
2. **改 query 合成 prompt**：去掉固定 2–4 doc 的约束，按 task type 指定 doc 需求数
3. **重新生成 test 和 train 数据**：用新的 excerpt + 灵活 doc 数
4. **重跑 constraint annotation**
5. **重跑全部模型评测 + SFT 训练**
6. **更新论文数据和图表**

---

## 5  风险

- 改 context sourcing = 整条 pipeline 重跑，工作量大
- 已有的 8 模型 leaderboard 数据全部作废，需要重新评测
- SFT 模型需要重训
- 时间评估：~1 周（含评测和论文更新）
