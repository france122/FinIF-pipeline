# Finance Workflow Task Taxonomy for Instruction-Following Benchmark

日期：2026-06-04

## 设计结论

建议采用 **5 个金融工作流阶段** 作为最终主线。

```text
Intake & Profiling
-> Research & Due Diligence
-> Decision & Structuring
-> Risk & Compliance Review
-> Execution, Monitoring, Reporting & Operations
```

这个划分的好处是：

- 覆盖金融任务从进入系统到后续监控的完整链条；
- 每个 workflow 都能自然对应不同类型的长 context；
- 每个阶段都有明确工作产物，方便构造 query 和 protocol；
- 广度足够，但不会散成职业百科。

说明：`Risk & Compliance Review` 在真实机构中是横向 gate，可能发生在 intake、decision、execution 和 monitoring 的任意阶段。这里把它单独列为一个 workflow，是为了让 benchmark 能稳定采样风险识别、合规审查、适当性判断、压力测试和升级报告等能力。

## 最终任务表

| Workflow | Workflow 对应任务 | Possible English Context Types and Sources |
| --- | --- | --- |
| **1. Intake & Profiling** | **KYC onboarding**：核验客户或企业身份、受益所有人、地址、制裁/PEP 风险。<br><br>**Client risk profiling**：根据收入、资产、负债、投资经验、风险承受能力、流动性需求建立客户画像。<br><br>**Loan application intake**：整理贷款申请、借款人基本信息、收入证明、企业财务资料、抵押品信息。<br><br>**Counterparty / issuer profile construction**：建立企业、交易对手、项目或发行人的基本面画像。<br><br>**Missing information checklist**：识别进入下一阶段前缺失的文件、字段或授权。<br><br>**Service scope explanation**：向客户说明服务范围、流程、限制和下一步，不提前承诺审批、收益或税务结果。 | **Customer documents**: customer intake form, onboarding questionnaire, identity documents, proof of address, beneficial ownership form, W-8/W-9 form.<br><br>**KYC / AML sources**: sanctions screening result, PEP screening result, adverse media summary, customer due diligence checklist, enhanced due diligence memo.<br><br>**Financial profile sources**: bank statements, brokerage account statements, insurance policies, tax status summary, income and expense worksheet, liabilities schedule.<br><br>**Loan intake sources**: loan application, borrower questionnaire, credit authorization form, collateral description, employment verification, corporate registration documents.<br><br>**Policy sources**: KYC policy excerpt, onboarding checklist, suitability questionnaire, customer classification policy, data privacy policy. |
| **2. Research & Due Diligence** | **Financial statement analysis**：分析资产负债表、利润表、现金流量表、财务比率和趋势。<br><br>**Industry and market research**：整理行业规模、竞争格局、宏观因素、利率、商品价格或市场环境。<br><br>**Earnings review**：阅读 earnings release、management commentary、analyst Q&A，提取业绩驱动因素和风险。<br><br>**Credit due diligence**：审查借款人财务、信用历史、偿债能力、抵押品和同业对比。<br><br>**Investment due diligence**：对公司、证券、基金、资产或项目进行尽调，识别投资 thesis、风险和关键假设。<br><br>**Background screening**：检查交易对手、管理层、发行人或项目方的背景、声誉、法律或监管风险。<br><br>**Due diligence checklist completion**：根据政策或交易要求判断尽调材料是否完整。 | **Company financial sources**: annual report, 10-K, 10-Q, earnings release, investor presentation, management discussion and analysis, audited financial statements.<br><br>**Market and industry sources**: industry report excerpt, market data table, macroeconomic indicators, interest rate curve, commodity price data, competitor benchmark table.<br><br>**Credit research sources**: credit report, borrower financial statements, bank statements, debt schedule, collateral appraisal, covenant schedule, peer comparison table.<br><br>**Investment research sources**: equity research note, bond offering memorandum, fund factsheet, term sheet, cap table, historical price series, analyst transcript excerpt.<br><br>**Diligence sources**: due diligence request list, data room index, legal summary, background check report, adverse media summary, management interview notes.<br><br>**Policy sources**: due diligence policy, investment committee checklist, credit policy excerpt, documentation standard. |
| **3. Decision & Structuring** | **Credit memo drafting**：基于研究和尽调结果形成授信建议，说明风险、偿债能力、抵押品、审批条件和升级项。<br><br>**Underwriting memo**：为贷款、保险、证券或项目融资形成 underwriting 判断。<br><br>**Loan approval package**：整理审批包，包括借款人概况、贷款用途、结构、担保、财务比率、例外事项。<br><br>**DCF valuation / pricing analysis**：基于现金流、贴现率、可比公司或证券价格形成估值和敏感性分析。<br><br>**Investment memo**：形成投资建议，区分事实、假设、风险、估值和推荐动作。<br><br>**Capital structure / financing proposal**：设计债务、股权、再融资或重组方案，比较金额、来源、期限和 trade-off。<br><br>**Portfolio proposal**：根据客户目标、风险承受能力和约束提出资产配置或再平衡方案。<br><br>**Trade order ticket preparation**：把客户交易意图转为结构化订单字段，并识别歧义或缺失字段。 | **Decision package sources**: credit memo template, underwriting guidelines, investment committee memo template, approval authority matrix, exception policy.<br><br>**Financial model sources**: DCF model output, valuation worksheet, comparable company table, comparable transaction table, sensitivity table, pricing model output.<br><br>**Loan structuring sources**: proposed loan terms, amortization schedule, collateral package, guarantor information, covenant package, loan approval form.<br><br>**Investment decision sources**: investment thesis notes, risk factor list, valuation assumptions, portfolio holdings, client investment policy statement, target allocation table.<br><br>**Capital markets sources**: term sheet, debt maturity schedule, refinancing proposal, rating agency considerations, market conditions memo, transaction timeline.<br><br>**Trading sources**: client order message, security master, price quote, account restrictions, order management policy, trade blotter template. |
| **4. Risk & Compliance Review** | **AML red-flag review**：识别异常交易、资金来源问题、制裁/PEP 风险、可疑活动或需要升级的客户行为。<br><br>**Covenant check**：核验财务 covenant、信息披露 covenant 或贷款条件是否被触发或违反。<br><br>**Suitability review**：判断产品、交易或组合是否匹配客户画像、风险承受能力、投资目标和集中度限制。<br><br>**Sales-script / communication compliance**：检查客户话术是否包含保证收益、误导性表述、遗漏披露或越权建议。<br><br>**Stress testing**：在指定情景下评估组合、贷款、交易或机构资产负债的潜在损失。<br><br>**Risk disclosure review**：检查发行文件、投资 memo 或客户材料中的风险披露是否充分。<br><br>**Internal control review**：识别审批、账务、交易、数据权限或职责分离中的控制缺陷。<br><br>**Regulatory issue escalation**：把疑似违规、重大风险或超权限事项整理为升级报告。 | **AML / compliance sources**: transaction monitoring alert, suspicious activity narrative, sanctions screening result, PEP screening result, adverse media summary, AML policy excerpt.<br><br>**Covenant and credit control sources**: covenant schedule, compliance certificate, borrower financial statements, waiver request, loan agreement excerpt.<br><br>**Suitability sources**: customer risk profile, product risk rating, holdings report, concentration report, investment policy statement, disclosure document.<br><br>**Communication review sources**: sales script, client email, call transcript, marketing material, required disclosure checklist, prohibited claims policy.<br><br>**Risk analytics sources**: portfolio holdings, VaR report, stress scenario definitions, sensitivity table, liquidity report, counterparty exposure report.<br><br>**Control and audit sources**: internal audit report, control matrix, access log, segregation of duties matrix, exception report, policy and procedure manual.<br><br>**Regulatory sources**: regulation excerpt, compliance manual, examination findings, remediation tracker, escalation policy. |
| **5. Execution, Monitoring, Reporting & Operations** | **Trade / loan / investment execution check**：复核交易、贷款或投资决策是否被正确落地，包括订单、确认、资金流、条件满足和异常项。<br><br>**Portfolio monitoring**：持续跟踪组合表现、风险暴露、集中度、漂移和再平衡需求。<br><br>**Post-investment / post-loan review**：复核投资或贷款执行后的表现、条件满足情况、风险变化和行动项。<br><br>**Risk alert generation**：根据阈值、limit breach、异常指标或新闻事件生成风险提醒。<br><br>**Client review report**：生成面向客户的定期报告，解释表现、费用、风险和下一步建议，避免保证性语言。<br><br>**Reconciliation**：核对交易、现金、持仓、费用、账簿、报表或外部托管数据的一致性。<br><br>**Month-end close / financial reporting support**：支持月结、分录、调节、报表复核和管理层报告。<br><br>**Board / regulatory reporting**：准备董事会、管理层或监管报告，标记缺失证据和不可确认事项。<br><br>**Remediation tracking**：跟踪审计、合规或风险问题的整改状态、owner、due date 和证据。 | **Execution sources**: trade confirmation, order ticket, trade blotter, settlement instruction, loan closing checklist, funding memo, wire instruction, investment allocation notice.<br><br>**Portfolio monitoring sources**: holdings report, performance report, benchmark return table, concentration report, risk dashboard, drift report, rebalance trigger list.<br><br>**Post-decision sources**: post-investment review memo, loan monitoring report, covenant compliance update, borrower performance update, action item tracker.<br><br>**Alert sources**: limit breach report, exception report, market news summary, rating downgrade notice, delinquency report, early warning indicator dashboard.<br><br>**Client reporting sources**: client statement, quarterly review deck, fee schedule, performance attribution report, tax lot report, disclosure language library.<br><br>**Reconciliation sources**: trade blotter, custodian statement, general ledger, cash ledger, settlement report, invoice records, journal entries.<br><br>**Financial reporting sources**: trial balance, month-end close checklist, adjusting entry log, variance analysis, management reporting package, regulatory reporting template.<br><br>**Remediation sources**: audit finding tracker, compliance remediation plan, control owner attestation, evidence upload log, board action register. |

## O*NET 职业来源映射

| Workflow | 主要 O*NET 职业 |
| --- | --- |
| Intake & Profiling | Personal Financial Advisors, 13-2052.00; Loan Officers, 13-2072.00; Compliance Officers, 13-1041.00 |
| Research & Due Diligence | Credit Analysts, 13-2041.00; Financial and Investment Analysts, 13-2051.00; Financial Risk Specialists, 13-2054.00; Accountants and Auditors, 13-2011.00 |
| Decision & Structuring | Credit Analysts, 13-2041.00; Loan Officers, 13-2072.00; Financial and Investment Analysts, 13-2051.00; Financial Quantitative Analysts, 13-2099.01; Financial Managers, 11-3031.00; Securities, Commodities, and Financial Services Sales Agents, 41-3031.00 |
| Risk & Compliance Review | Financial Risk Specialists, 13-2054.00; Financial Examiners, 13-2061.00; Compliance Officers, 13-1041.00; Accountants and Auditors, 13-2011.00 |
| Execution, Monitoring, Reporting & Operations | Financial Managers, 11-3031.00; Accountants and Auditors, 13-2011.00; Securities, Commodities, and Financial Services Sales Agents, 41-3031.00; Personal Financial Advisors, 13-2052.00; Financial Risk Specialists, 13-2054.00 |

## 推荐样本占比

| Workflow | 建议样本占比 | 主要能力 |
| --- | ---: | --- |
| Intake & Profiling | 15% | 信息抽取、缺失识别、客户画像、权限边界 |
| Research & Due Diligence | 20% | 多文档阅读、财报/行业分析、尽调、证据整理 |
| Decision & Structuring | 25% | memo 写作、估值、审批建议、方案设计、结构化输出 |
| Risk & Compliance Review | 25% | 风险识别、压力测试、合规检查、适当性、升级判断 |
| Execution, Monitoring, Reporting & Operations | 15% | 执行复核、持续监控、报告生成、账务核对、运营审查 |

## 任务体系使用方式

每个 benchmark item 都从一个具体的 workflow、task 和 work product 出发，而不是先写 query 或先拼 constraints。

推荐生成顺序：

```text
workflow + task + deliverable
-> select / synthesize context
-> write query
-> extract constraints from context + query
-> build protocol
```

这里最重要的变化是：`constraint` 不再预先分类和手工拼装，而是作为从样本中抽出来的中间表示，服务于后续 protocol 生成。

推荐 item schema：

```yaml
workflow: Risk & Compliance Review
task: AML red-flag review
work_product: compliance escalation report
context_types:
  - transaction monitoring alert
  - customer due diligence checklist
  - sanctions screening result
  - AML policy excerpt
query: >
  Review the provided materials and prepare a compliance escalation report.
  Identify suspicious signals, cite the supporting evidence, and recommend
  whether the case should be escalated.
extracted_constraints:
  - output must be a compliance escalation report
  - use only the provided materials
  - cite evidence for each suspicious signal
  - recommend escalation when high-risk issues remain unresolved
evaluation_dimensions:
  - delivery_quality
  - instruction_adherence
```

## 评测维度

当前建议只保留两个主维度：

- `delivery_quality`
- `instruction_adherence`

定义如下：

`delivery_quality`

- 衡量最终交付件本身是否可靠、完整、可用。
- 对计算或核验型任务，它包括事实、抽取、计算、规则匹配是否正确。
- 对分析或报告生成型任务，它包括分析是否合理、结论是否有依据、结构是否完整、是否适合目标读者和后续工作流使用。

`instruction_adherence`

- 衡量模型是否遵守 query 明确提出的要求，以及 context 中被明确触发的要求。
- 它主要关注格式、必需字段、输出风格、只用给定材料、证据引用、权限边界、升级规则、拒绝条件等。

也就是说，这个 benchmark 最终评的是两件事：

1. 这个金融交付件做得好不好。
2. 这个交付件是不是按要求做出来的。

## 数据合成计划

### 背景和设计意图

本 benchmark 的目标不是测试模型是否“懂金融术语”，而是测试模型在金融工作流节点上的 instruction following 能力。

这里的“工作流”是组织任务和构造场景的框架，不代表我们在评测完整 end-to-end workflow。真正的评测单位是一个个具体的金融交付任务，例如：

- KYC review
- credit memo
- investment memo
- suitability check
- reconciliation report

这些任务共享一个特点：它们不是开放问答，而是需要模型在一个工作流节点上，基于指定材料，产出一个受格式、证据、权限和合规要求约束的交付件。

因此，合成流程不应该从“随便找一个金融问题”开始，而应该从真实任务开始：

```text
workflow -> task -> work product -> context -> query -> extracted constraints -> protocol
```

### 合成总体路线

每条样本建议按以下顺序生成：

```text
1. 选择 workflow
2. 选择 workflow 下的具体任务
3. 确定工作产物 work product
4. select / synthesize context pack
5. 根据 context 和 work product 写 query
6. 从 context 和 query 中抽取 constraints
7. 根据 extracted constraints 生成 evaluation protocol
8. 做质量检查和去重
```

这里不要反过来从 query 开始，也不要先设计 constraint taxonomy。query 应该是 context 和 work product 的自然结果，constraint 应该是从样本中抽取出来的，而不是预先附会进去的。

### Step 1：选择 workflow 和任务

使用本文件中的 5 个 workflow：

- `Intake & Profiling`
- `Research & Due Diligence`
- `Decision & Structuring`
- `Risk & Compliance Review`
- `Execution, Monitoring, Reporting & Operations`

建议第一版样本占比：

- `Intake & Profiling`: 15%
- `Research & Due Diligence`: 20%
- `Decision & Structuring`: 25%
- `Risk & Compliance Review`: 25%
- `Execution, Monitoring, Reporting & Operations`: 15%

优先覆盖表格第二列中的任务，例如：

- `KYC onboarding`
- `Credit memo drafting`
- `DCF valuation / pricing analysis`
- `AML red-flag review`
- `Reconciliation`

### Step 2：确定工作产物

每个任务都必须先绑定一个明确 work product。work product 决定 query 的形态，也决定后续 protocol 的结构。

示例映射：

| Task | Work product |
| --- | --- |
| KYC onboarding | KYC review note |
| Client risk profiling | client risk profile |
| Loan application intake | missing-document checklist |
| Financial statement analysis | financial analysis summary |
| Credit due diligence | due diligence checklist |
| Credit memo drafting | internal credit memo |
| DCF valuation / pricing analysis | valuation summary |
| Investment memo | investment committee memo |
| Trade order ticket preparation | structured order ticket |
| AML red-flag review | compliance escalation report |
| Covenant check | covenant compliance note |
| Suitability review | suitability review note |
| Stress testing | stress-test summary |
| Portfolio monitoring | portfolio monitoring report |
| Reconciliation | reconciliation exception report |
| Month-end close | close review memo |

### Step 3：选择或合成 context pack

context pack 是每条样本的核心。它应该模拟真实金融任务中的材料组合，而不是只给一个问题背景。

如果由我继续 sourcing：

- 优先使用公开、可引用、非敏感来源。
- 公司财报类使用公开 filings、annual reports、earnings releases、investor presentations。
- 市场和宏观数据可使用公开表格或可控的简化合成表。
- KYC、AML、审批权限、适当性、covenant、内部政策等建议合成，以便控制触发条件和 gold protocol。
- 客户隐私、银行流水、税务资料、贷款申请等必须合成，不使用真实个人数据。

如果由另一个 agent 接手：

- 先从本文件第三列 `Possible English Context Types and Sources` 中选 3-6 类 context source。
- 每条样本至少包含一个主文档、一个规则/政策文档、一个结构化数据表。
- 至少 40% 样本应为 multi-document。
- 至少 50% 样本应为 long-context。
- 至少 25% 样本应包含计算、调节或阈值判断。
- 至少 25% 样本应包含合规、升级、拒绝或权限边界。

推荐 context pack 结构：

```yaml
context_pack:
  documents:
    - id: DOC1
      type: borrower financial statements
      content: ...
    - id: DOC2
      type: credit policy excerpt
      content: ...
    - id: DOC3
      type: collateral appraisal summary
      content: ...
  tables:
    - id: TBL1
      type: covenant schedule
      content: ...
  metadata:
    workflow: Decision & Structuring
    task: Credit memo drafting
    source_mode: synthetic / public / mixed
```

### Step 4：根据 context 写 query

query 是要求模型产出 work product 的任务指令，不是一个随便的问题。

通用模板：

```text
You are acting as a [role].
Using only the provided context, prepare a [work product] for [audience].
Your output must include [required sections].
```

例子：

```text
You are acting as a credit analyst.
Using only the provided loan package, prepare an internal credit memo for the credit committee.
Include borrower overview, key financial ratios, repayment capacity, collateral assessment,
policy exceptions, missing information, and an approve/reject/escalate recommendation.
```

不同 workflow 的 query 常见形式：

| Workflow | Query 类型 |
| --- | --- |
| Intake & Profiling | complete checklist, build profile, classify onboarding risk, draft client next-step email |
| Research & Due Diligence | summarize financials, complete diligence checklist, extract risks, compare peers |
| Decision & Structuring | draft memo, prepare valuation summary, structure options, build approval package |
| Risk & Compliance Review | review red flags, check covenant, review suitability, classify severity, draft escalation |
| Execution, Monitoring, Reporting & Operations | reconcile records, generate monitoring report, produce risk alert, draft client review |

### Step 5：从 context 和 query 中抽取 constraints

当前阶段不预先规定 constraint taxonomy。

我们采用更自然的方式：先有 context 和 query，再从中抽取约束。抽取出来的 constraint 主要用于构造 protocol，而不是一开始就作为一套固定标签硬塞给样本。

constraint 的来源主要有两种：

1. query 里明确写出来的要求。
2. context 中被明确触发的要求。

例子一：

```text
Query: Output the answer as a JSON object with fields:
risk_level, evidence, next_action.
```

抽出的 constraint：

- output must be JSON
- required fields are risk_level, evidence, next_action

例子二：

```text
Policy: Loans above $500,000 require manager approval.
Requested amount: $750,000.
```

抽出的 constraint：

- recommendation must be escalate rather than final approve

例子三：

```text
Client risk tolerance: Conservative.
Proposed product: leveraged ETF.
```

抽出的 constraint：

- response must identify a suitability conflict
- response must not recommend proceeding without escalation or additional review

例子四：

```text
Custodian statement cash balance: $1,250,000.
Internal ledger cash balance: $1,205,000.
```

抽出的 constraint：

- response must flag a $45,000 reconciliation exception
- response must not mark the account as reconciled

后续如果需要分析 constraint taxonomy，可以在抽取完成后再做归纳，而不是在样本生成前先验规定。

### Step 6：根据 extracted constraints 生成 evaluation protocol

每条样本都必须有可评分 protocol。protocol 的职责不是判断“回答像不像”，而是把该任务可核验的要求结构化。

推荐 protocol 结构：

```yaml
evaluation_protocol:
  required_outputs:
    - section or field names
  extracted_constraints:
    - explicit query requirements
    - context-triggered requirements
  factual_checks:
    - expected facts or evidence ids
  numerical_checks:
    - formula
    - expected value
    - tolerance
  grounding_checks:
    - claim -> evidence document ids
  delivery_quality_checks:
    - completeness
    - clarity
    - usefulness for intended audience
  instruction_adherence_checks:
    - format compliance
    - required fields included
    - escalation / refusal followed
```

### Step 7：质量控制

合成后需要检查：

- workflow 和 task 是否匹配。
- context 是否足以支持 query。
- query 是否真的要求一个明确 work product。
- extracted constraints 是否都能从 query 或 context 中找到依据。
- 是否存在无法评分的开放性问题。
- protocol 是否不依赖外部知识。
- 数值答案是否可复算。
- 需要升级或拒绝的样本是否真的存在触发条件。
- 客户或个人数据是否全部为合成数据。
- 不同样本之间是否只是换名重复。

### 建议第一批合成规模

建议先做 pilot，而不是直接大规模铺开：

- 每个 workflow 选 3 个任务。
- 每个任务合成 5 条样本。
- 总计 `5 x 3 x 5 = 75` 条 pilot 样本。

pilot 通过后再扩展：

- 每个 workflow 选 4-6 个任务。
- 每个任务合成 10-20 条样本。
- 总计约 250-500 条正式 v1 样本。

### 给下一个 agent 的接手说明

如果你是接手合成的 agent，请不要重新设计 taxonomy。当前 taxonomy 已经确定：

```text
1. Intake & Profiling
2. Research & Due Diligence
3. Decision & Structuring
4. Risk & Compliance Review
5. Execution, Monitoring, Reporting & Operations
```

你的任务不是重写工作流，而是基于这个 taxonomy 生成可评测的数据实例。

每条数据都应从一个 workflow 和一个具体 task 出发，绑定一个 work product，然后：

1. 选择或合成 context pack。
2. 基于 context 写 query。
3. 从 context 和 query 中抽取 constraints。
4. 根据 extracted constraints 生成 evaluation protocol。

优先做能体现金融 IF 难度的样本：

- 长 context；
- 多文档；
- 证据分散；
- 有无关干扰信息；
- 有缺失或冲突信息；
- 有政策阈值；
- 有权限边界；
- 有计算；
- 有合规或升级要求；
- 有固定输出格式。

不要生成只需要常识回答的金融问答，也不要生成没有明确评分标准的开放式建议题。

## Abstract 组织逻辑

论文 abstract 建议按下面四段组织，而不是一上来讲方法细节：

### 第一段：问题设置

金融是LLM应用的重要场景

很多金融任务通常要求模型：

- 读取指定材料；
- 在一个工作流节点上完成任务；
- 产出一个明确交付件；
- 同时满足格式、证据、权限和合规要求。

### 第二段：现有问题

观察到，强模型在这种任务上并不稳定。

它们可能能找到相关事实，但仍然会：

- 漏掉证据；
- 忽略触发条件；
- 越权；
- 过度下结论；
- 输出不像要求的 artifact。

这一段要把问题定义成“交付能力不稳”，而不是单纯“知识不够”。

### 第三段：我们做了什么

第三段再介绍 FinIF。

这里最自然的说法是：

- FinIF 是一个面向金融 instruction following 的 benchmark 和训练语料；
- 它以金融生命周期 workflow 组织任务；
- 每个样本是一个 workflow-grounded deliverable；
- 包含 FinIF-Test 和 FinIF-Train；
- 通过可扩展数据管线生成 context、query、extracted constraints 和 protocol。

### 第四段：怎么评和有什么发现

最后再讲评测维度和实验发现。

当前建议只突出两个维度：

- `delivery_quality`
- `instruction_adherence`

然后一句话说明：

- `delivery_quality` 看这个金融交付件本身做得好不好；
- `instruction_adherence` 看它是否按要求做出来。

最后再收束到实验发现：FinIF 能揭示强模型在金融 IF 上的系统性短板，而 FinIF-Train 能显著提升相关能力。
