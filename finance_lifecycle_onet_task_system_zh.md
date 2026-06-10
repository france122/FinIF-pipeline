# 金融生命周期主线版 O*NET 任务体系

日期：2026-06-04

## 0. 推荐主线

本版本采用 **金融生命周期工作流** 作为 benchmark 主叙事，而不是以职业分类作为一级结构。

理由：

- 你们的核心假设是：金融任务的 instruction following 难点来自真实工作流中的长 context、多文档、多约束、权限边界、合规风险和可验证工作产物。
- O*NET 职业和任务适合作为来源层，但最终 benchmark 应该体现“人在金融机构里如何完成一串工作”。
- 因此，本体系采用“广度大于深度”的设计：覆盖多个金融职业，但只保留每个职业最能支撑 workflow 的 O*NET 原始任务。

最终主线：

```text
金融生命周期 workflow
  -> 涉及 O*NET 职业
  -> O*NET 原始任务描述，英文原文 + 中文翻译
  -> 重写后的 benchmark 原子任务族
  -> 工作产物
  -> 金融约束
  -> 评测规则
```

本版本暂不展开 query -> context 生成细节，只保留“任务体系”本身。

## 1. Workflow A：客户 / 交易对手 Intake & Profiling

### 1.1 真实工作流含义

这一阶段发生在金融服务开始前：收集客户或交易对手资料，理解目标、风险承受能力、财务状态、申请材料完整性和合规前置要求。

它适合测：

- 长 context 中的信息抽取；
- 缺失材料识别；
- KYC / suitability / 权限边界；
- 客户画像构建；
- 不过早给出投资、贷款或税务结论。

### 1.2 涉及 O*NET 职业

#### Personal Financial Advisors, 13-2052.00

O*NET 职业描述：

> Advise clients on financial plans using knowledge of tax and investment strategies, securities, insurance, pension plans, and real estate.

中文翻译：运用税务、投资策略、证券、保险、养老金计划和房地产等知识，为客户提供财务计划建议。

O*NET 原始任务：

1. EN: "Interview clients to determine their current income, expenses, insurance coverage, tax status, financial objectives, risk tolerance, or other information needed to develop a financial plan."
   CN: 访谈客户，了解其当前收入、支出、保险覆盖、税务状态、财务目标、风险承受能力或制定财务计划所需的其他信息。

2. EN: "Explain to clients the personal financial advisor's responsibilities and the types of services to be provided."
   CN: 向客户解释个人财务顾问的职责以及将提供的服务类型。

3. EN: "Guide clients in the gathering of information, such as bank, tax, pension, insurance, or estate documents."
   CN: 指导客户收集银行、税务、养老金、保险或遗产相关文件。

#### Loan Officers, 13-2072.00

O*NET 职业描述：

> Evaluate, authorize, or recommend approval of commercial, real estate, or credit loans.

中文翻译：评估、授权或建议批准商业贷款、房地产贷款或信用贷款。

O*NET 原始任务：

1. EN: "Meet with applicants to obtain information for loan applications and to answer questions about the process."
   CN: 与申请人会面，获取贷款申请信息，并回答关于流程的问题。

2. EN: "Obtain and compile copies of loan applicants' credit histories, corporate financial statements, and other financial information."
   CN: 获取并汇编贷款申请人的信用历史、企业财务报表和其他财务信息。

3. EN: "Review and update credit and loan files."
   CN: 审查并更新信用和贷款文件。

#### Compliance Officers, 13-1041.00

O*NET 职业描述：

> Examine, evaluate, and investigate eligibility for or conformity with laws and regulations governing contract compliance of licenses and permits.

中文翻译：检查、评估并调查资格或合规性，以确认是否符合法律法规对合同、许可和执照合规的要求。

O*NET 原始任务：

1. EN: "Evaluate applications, records, or documents to gather information about eligibility or liability issues."
   CN: 评估申请、记录或文件，以收集关于资格或责任问题的信息。

2. EN: "Identify compliance issues that require follow-up or investigation."
   CN: 识别需要跟进或调查的合规问题。

3. EN: "Verify that all firm and regulatory policies and procedures have been documented, implemented, and communicated."
   CN: 核验公司和监管政策程序是否已被记录、实施并传达。

### 1.3 Benchmark 原子任务族

#### A-01 客户资料完整性检查

- 来源职业：Personal Financial Advisors, Loan Officers, Compliance Officers
- 来源任务：访谈客户、收集文件、评估申请/记录、更新贷款文件
- 工作产物：missing-information checklist / intake completeness report
- 金融约束：只标记真实缺失项；区分必需项和可选项；不得提前给出批准、投资或税务结论
- 评测规则：字段抽取正确性、缺失项识别、最小化追问、隐私与权限边界

#### A-02 客户财务画像构建

- 来源职业：Personal Financial Advisors
- 来源任务：访谈客户以确定收入、支出、保险、税务状态、目标和风险承受能力
- 工作产物：client financial profile
- 金融约束：区分已核实事实、客户陈述和模型推断；不得做产品推荐
- 评测规则：画像完整性、证据 grounding、事实/推断分离、格式遵循

#### A-03 KYC / 合规前置分诊

- 来源职业：Compliance Officers
- 来源任务：评估申请/记录/文件，识别需要跟进或调查的合规问题
- 工作产物：compliance triage log
- 金融约束：标记需要升级的问题；保护隐私；不得做无依据违规指控
- 评测规则：合规 issue 召回率、严重性分类、证据引用、升级判断

#### A-04 服务范围与客户沟通说明

- 来源职业：Personal Financial Advisors, Loan Officers
- 来源任务：解释顾问职责、服务类型、贷款流程
- 工作产物：client-facing explanation
- 金融约束：通俗语言；不得保证收益、批准或税务结果；说明下一步流程
- 评测规则：语气合规、禁止承诺识别、客户可理解性、信息完整性

## 2. Workflow B：Credit & Underwriting

### 2.1 真实工作流含义

这一阶段围绕贷款、授信和信用风险判断：分析借款人财务、信用历史、抵押品、行业对比、covenant 和审批权限，形成授信建议或升级判断。

它适合测：

- 多文档长 context；
- 财务比率计算；
- 政策阈值匹配；
- 缺失/冲突信息处理；
- approve / reject / escalate 的边界判断。

### 2.2 涉及 O*NET 职业

#### Credit Analysts, 13-2041.00

O*NET 职业描述：

> Analyze credit data and financial statements of individuals or firms to determine the degree of risk involved in extending credit or lending money.

中文翻译：分析个人或企业的信用数据和财务报表，以判断发放信用或贷款所涉及的风险程度。

O*NET 原始任务：

1. EN: "Analyze credit data and financial statements to determine the degree of risk involved in extending credit or lending money."
   CN: 分析信用数据和财务报表，以判断发放信用或贷款所涉及的风险程度。

2. EN: "Complete loan applications, including credit analyses and summaries of loan requests, and submit to loan committees for approval."
   CN: 完成贷款申请，包括信用分析和贷款请求摘要，并提交贷款委员会批准。

3. EN: "Generate financial ratios, using computer programs, to evaluate customers' financial status."
   CN: 使用计算机程序生成财务比率，以评估客户财务状况。

4. EN: "Prepare reports that include the degree of risk involved in extending credit or lending money."
   CN: 准备报告，说明发放信用或贷款所涉及的风险程度。

5. EN: "Compare liquidity, profitability, and credit histories of establishments being evaluated with those of similar establishments in the same industries and geographic locations."
   CN: 将被评估机构的流动性、盈利能力和信用历史与同一行业、同一地区的类似机构进行比较。

#### Loan Officers, 13-2072.00

O*NET 职业描述：

> Advise borrowers on financial status and payment methods.

中文翻译：就财务状态和还款方式向借款人提供说明或建议。

O*NET 原始任务：

1. EN: "Analyze applicants' financial status, credit, and property evaluations to determine feasibility of granting loans."
   CN: 分析申请人的财务状态、信用状况和房产/抵押物评估，以判断授予贷款的可行性。

2. EN: "Approve loans within specified limits, and refer loan applications outside those limits to management for approval."
   CN: 在规定权限范围内批准贷款，并将超出权限的贷款申请提交管理层审批。

3. EN: "Explain to customers the different types of loans and credit options that are available, as well as the terms of those services."
   CN: 向客户解释可用的不同贷款类型、信用选项以及相关服务条款。

4. EN: "Compute payment schedules."
   CN: 计算还款计划。

#### Financial Managers, 11-3031.00

O*NET 职业描述：

> Plan, direct, or coordinate accounting, investing, banking, insurance, securities, and other financial activities of a branch, office, or department.

中文翻译：计划、指导或协调分支机构、办公室或部门的会计、投资、银行、保险、证券和其他金融活动。

O*NET 原始任务：

1. EN: "Approve, reject, or coordinate the approval or rejection of lines of credit or commercial, real estate, or personal loans."
   CN: 批准、拒绝或协调批准/拒绝信用额度、商业贷款、房地产贷款或个人贷款。

2. EN: "Examine, evaluate, or process loan applications."
   CN: 审查、评估或处理贷款申请。

3. EN: "Prepare financial or regulatory reports required by laws, regulations, or boards of directors."
   CN: 准备法律、法规或董事会要求的财务或监管报告。

### 2.3 Benchmark 原子任务族

#### B-01 借款人信用风险评估

- 来源职业：Credit Analysts, Loan Officers
- 来源任务：分析信用数据、财务报表、申请人财务状态、信用和抵押物评估
- 工作产物：credit memo
- 金融约束：只使用给定文件；引用证据；明确 approve / reject / escalate；不得承诺审批结果
- 评测规则：风险识别、证据 grounding、决策边界、格式遵循

#### B-02 财务比率和偿债能力核验

- 来源职业：Credit Analysts
- 来源任务：生成财务比率以评估客户财务状态
- 工作产物：ratio table / debt-service analysis
- 金融约束：展示公式；保留单位；处理缺失科目；不得编造数字
- 评测规则：计算准确性、公式正确性、缺失数据处理、数值一致性

#### B-03 贷款审批权限与升级判断

- 来源职业：Loan Officers, Financial Managers
- 来源任务：在权限内批准贷款，超出权限提交管理层；批准/拒绝或协调贷款决策
- 工作产物：approval / escalation note
- 金融约束：严格遵守权限上限；例外项需升级；客户话术不得承诺结果
- 评测规则：权限判断、例外识别、升级正确性、客户安全表达

#### B-04 同业比较与贷款盈利性摘要

- 来源职业：Credit Analysts
- 来源任务：比较流动性、盈利能力和信用历史；分析收入增长、管理质量、市场份额等盈利性因素
- 工作产物：peer comparison appendix / profitability risk summary
- 金融约束：区分事实、比较和推断；引用 benchmark；不得做无依据因果解释
- 评测规则：比较准确性、风险排序、推断边界、证据使用

#### B-05 贷款条款与还款计划解释

- 来源职业：Loan Officers
- 来源任务：解释贷款类型和信用选项；计算还款计划
- 工作产物：client-facing loan explanation
- 金融约束：通俗语言；披露费用/利率/还款义务；不得误导或保证批准
- 评测规则：还款计算、披露完整性、语气合规、客户可理解性

## 3. Workflow C：Investment & Trading Decision

### 3.1 真实工作流含义

这一阶段覆盖投资研究、估值、融资方案、交易指令解析和交易前检查。它不只测“会不会写投资 memo”，更关注模型是否能在多源 context 中区分事实、假设、建议、风险和合规边界。

它适合测：

- 投资研究长 context；
- 估值和敏感性；
- 交易指令结构化；
- 适当性和限制产品检查；
- 不保证收益、不执行歧义指令。

### 3.2 涉及 O*NET 职业

#### Financial and Investment Analysts, 13-2051.00

O*NET 职业描述：

> Conduct quantitative analyses of information involving investment programs or financial data of public or private institutions, including valuation of businesses.

中文翻译：对涉及投资项目或公私机构财务数据的信息进行定量分析，包括企业估值。

O*NET 原始任务：

1. EN: "Advise clients on aspects of capitalization, such as amounts, sources, or timing."
   CN: 就资本化安排的金额、来源或时点等方面向客户提供建议。

2. EN: "Analyze financial or operational performance of companies facing financial difficulties to identify or recommend remedies."
   CN: 分析陷入财务困境公司的财务或运营表现，以识别或推荐补救措施。

3. EN: "Assess companies as investments for clients by examining company facilities."
   CN: 通过考察公司设施，为客户评估公司作为投资标的的情况。

4. EN: "Prepare plans of action for investment, using financial analyses."
   CN: 基于财务分析准备投资行动计划。

5. EN: "Interpret data on price, yield, stability, future investment-risk trends, economic influences, and other factors affecting investment programs."
   CN: 解读价格、收益率、稳定性、未来投资风险趋势、经济影响以及其他影响投资项目的因素。

#### Securities, Commodities, and Financial Services Sales Agents, 41-3031.00

O*NET 职业描述：

> Buy and sell securities or commodities in investment and trading firms, or provide financial services to businesses and individuals.

中文翻译：在投资和交易机构买卖证券或商品，或为企业和个人提供金融服务。

O*NET 原始任务：

1. EN: "Make bids or offers to buy or sell securities."
   CN: 对买入或卖出证券提出买价或卖价。

2. EN: "Monitor markets or positions."
   CN: 监控市场或持仓。

3. EN: "Keep accurate records of transactions."
   CN: 保持准确的交易记录。

4. EN: "Complete sales order tickets and submit for processing of client-requested transactions."
   CN: 完成销售订单票据，并提交处理客户请求的交易。

5. EN: "Offer advice on the purchase or sale of particular securities."
   CN: 就特定证券的买入或卖出提供建议。

6. EN: "Explain stock market terms or trading practices to clients."
   CN: 向客户解释股票市场术语或交易实践。

#### Financial Quantitative Analysts, 13-2099.01

O*NET 职业描述：

> Develop quantitative techniques to inform securities investing, equities investing, pricing, or valuation of financial instruments.

中文翻译：开发定量技术，用于支持证券投资、股票投资、金融工具定价或估值。

O*NET 原始任务：

1. EN: "Apply mathematical or statistical techniques to address practical issues in finance, such as derivative valuation, securities trading, risk management, or financial market regulation."
   CN: 运用数学或统计技术解决金融中的实际问题，例如衍生品估值、证券交易、风险管理或金融市场监管。

2. EN: "Research or develop analytical tools to address issues such as portfolio construction or optimization, performance measurement, attribution, profit and loss measurement, or pricing models."
   CN: 研究或开发分析工具，以解决组合构建或优化、绩效衡量、归因、盈亏衡量或定价模型等问题。

3. EN: "Interpret results of financial analysis procedures."
   CN: 解读金融分析程序的结果。

### 3.3 Benchmark 原子任务族

#### C-01 投资研究 memo

- 来源职业：Financial and Investment Analysts
- 来源任务：解释价格、收益率、稳定性、投资风险趋势和经济影响；基于财务分析准备投资行动计划
- 工作产物：investment memo
- 金融约束：区分事实、假设、推断和建议；不得使用外部事实；列出关键风险
- 评测规则：证据 grounding、风险完整性、结论与证据一致、格式遵循

#### C-02 估值与敏感性摘要

- 来源职业：Financial and Investment Analysts, Financial Quantitative Analysts
- 来源任务：进行投资相关定量分析；应用数学或统计技术解决估值、定价问题
- 工作产物：valuation summary / sensitivity note
- 金融约束：展示关键假设；标记数据缺口；不得夸大模型精度
- 评测规则：数值一致性、假设透明度、敏感性推理、不确定性处理

#### C-03 融资与资本结构建议

- 来源职业：Financial and Investment Analysts
- 来源任务：就融资金额、来源、时点提供建议；分析困境公司并推荐补救措施
- 工作产物：capitalization recommendation / restructuring memo
- 金融约束：比较替代方案；区分流动性和偿付能力；说明 trade-off
- 评测规则：方案适配性、约束满足、风险提示、推理链完整性

#### C-04 交易指令解析与订单票据

- 来源职业：Securities, Commodities, and Financial Services Sales Agents
- 来源任务：提出买卖报价；完成 sales order tickets；保持准确交易记录
- 工作产物：structured order ticket
- 金融约束：不得执行歧义订单；缺失字段需标记；受限产品需升级
- 评测规则：字段抽取、歧义识别、限制产品识别、结构化格式

#### C-05 交易前适当性检查

- 来源职业：Securities Sales Agents, Personal Financial Advisors, Compliance Officers
- 来源任务：就买卖特定证券提供建议；向客户解释交易实践；评估合规问题
- 工作产物：pre-trade suitability note
- 金融约束：客户风险画像优先；不得推荐不适当产品；包含必要披露
- 评测规则：适当性判断、冲突识别、合规话术、升级处理

#### C-06 模型结果解释

- 来源职业：Financial Quantitative Analysts
- 来源任务：解释金融分析程序结果；研究或开发分析工具
- 工作产物：model interpretation note
- 金融约束：区分模型输出和投资建议；标记模型限制和验证缺口
- 评测规则：结果解释准确性、限制识别、边界遵循、技术内容压缩

## 4. Workflow D：Risk & Compliance Review

### 4.1 真实工作流含义

这一阶段覆盖金融风险识别、压力测试、风险披露、金融机构检查、内部控制和合规升级。它是最能体现“长 context + 多约束 + 高风险输出边界”的主线。

它适合测：

- 风险 taxonomy；
- 证据引用；
- 情景/压力测试；
- 合规规则映射；
- 内部控制缺陷；
- 安全拒绝或升级。

### 4.2 涉及 O*NET 职业

#### Financial Risk Specialists, 13-2054.00

O*NET 职业描述：

> Analyze and measure exposure to credit and market risk threatening the assets, earning capacity, or economic state of an organization.

中文翻译：分析和衡量信用风险、市场风险等对组织资产、盈利能力或经济状态的威胁。

O*NET 原始任务：

1. EN: "Analyze areas of potential risk to the assets, earning capacity, or success of organizations."
   CN: 分析可能影响组织资产、盈利能力或成功的潜在风险区域。

2. EN: "Conduct statistical analyses to quantify risk, using statistical analysis software or econometric models."
   CN: 使用统计分析软件或计量经济模型进行统计分析，以量化风险。

3. EN: "Devise scenario analyses reflecting possible severe market events."
   CN: 设计反映潜在严重市场事件的情景分析。

4. EN: "Identify key risks and mitigating factors of potential investments, such as asset types and values, legal and ownership structures, professional reputations, customer bases, or industry segments."
   CN: 识别潜在投资的关键风险和缓释因素，例如资产类型和价值、法律和所有权结构、专业声誉、客户基础或行业细分。

5. EN: "Produce reports or presentations that outline findings, explain risk positions, or recommend changes."
   CN: 产出报告或展示材料，概述发现、解释风险头寸或建议变更。

6. EN: "Review or draft risk disclosures for offer documents."
   CN: 审查或起草发行文件中的风险披露。

#### Financial Examiners, 13-2061.00

O*NET 职业描述：

> Enforce or ensure compliance with laws and regulations governing financial and securities institutions and financial and real estate transactions.

中文翻译：执行或确保金融机构、证券机构以及金融和房地产交易符合相关法律法规。

O*NET 原始任务：

1. EN: "Recommend actions to ensure compliance with laws and regulations, or to protect solvency of institutions."
   CN: 建议行动，以确保遵守法律法规或保护机构偿付能力。

2. EN: "Prepare reports, exhibits, and other supporting schedules that detail an institution's safety and soundness, compliance with laws and regulations, and recommended solutions to questionable financial conditions."
   CN: 准备报告、附件和支持性明细，详细说明机构安全稳健性、法律法规合规情况，以及针对可疑财务状况的建议解决方案。

3. EN: "Review balance sheets, operating income and expense accounts, and loan documentation to confirm institution assets and liabilities."
   CN: 审查资产负债表、营业收入和费用账户以及贷款文件，以确认机构资产和负债。

4. EN: "Review audit reports of internal and external auditors to monitor adequacy of scope of reports or to discover specific weaknesses in internal routines."
   CN: 审查内部和外部审计报告，以监控报告范围是否充分，或发现内部流程中的具体弱点。

#### Accountants and Auditors, 13-2011.00

O*NET 职业描述：

> Examine, analyze, and interpret accounting records to prepare financial statements, give advice, or audit and evaluate statements prepared by others.

中文翻译：检查、分析和解释会计记录，以准备财务报表、提供建议，或审计并评估他人编制的报表。

O*NET 原始任务：

1. EN: "Prepare detailed reports on audit findings."
   CN: 准备关于审计发现的详细报告。

2. EN: "Report to management about asset utilization and audit results, and recommend changes in operations and financial activities."
   CN: 向管理层报告资产利用和审计结果，并建议运营和财务活动变更。

3. EN: "Inspect account books and accounting systems for efficiency, effectiveness, and use of accepted accounting procedures."
   CN: 检查账簿和会计系统，判断其效率、有效性以及是否使用公认会计程序。

4. EN: "Examine records and interview workers to ensure recording of transactions and compliance with laws and regulations."
   CN: 审查记录并访谈员工，以确保交易记录正确并符合法律法规。

### 4.3 Benchmark 原子任务族

#### D-01 风险识别与风险登记

- 来源职业：Financial Risk Specialists
- 来源任务：分析潜在风险区域；识别关键风险和缓释因素
- 工作产物：risk register
- 金融约束：使用给定 taxonomy；引用证据；区分暴露、影响和缓释措施
- 评测规则：风险召回率、分类准确性、证据 grounding、缓释相关性

#### D-02 压力测试与情景分析摘要

- 来源职业：Financial Risk Specialists, Financial Quantitative Analysts
- 来源任务：量化风险；设计严重市场事件情景分析；应用统计技术
- 工作产物：stress-test summary
- 金融约束：只使用给定情景；标记缺失敏感性；不得夸大确定性
- 评测规则：情景遵循、计算准确性、驱动因素解释、不确定性处理

#### D-03 风险披露审查

- 来源职业：Financial Risk Specialists
- 来源任务：审查或起草发行文件中的风险披露
- 工作产物：risk disclosure review note
- 金融约束：标记遗漏的重大风险；避免给出最终法律意见；引用 context 证据
- 评测规则：重大风险覆盖、遗漏识别、法律边界、证据引用

#### D-04 金融机构安全稳健性检查

- 来源职业：Financial Examiners
- 来源任务：审查资产负债表、收入费用账户、贷款文件；准备安全稳健性与合规报告
- 工作产物：safety-and-soundness report section
- 金融约束：区分合规、偿付能力、运营控制问题；每个 finding 需证据支撑
- 评测规则：问题分类、证据映射、补救建议适配、严重性校准

#### D-05 内部控制缺陷与审计发现

- 来源职业：Financial Examiners, Accountants and Auditors
- 来源任务：审查审计报告；检查账簿和会计系统；准备审计发现报告
- 工作产物：control weakness memo / audit findings table
- 金融约束：区分 finding、risk、recommendation；避免无依据欺诈指控
- 评测规则：发现有效性、控制目标映射、严重性、不过度推断

#### D-06 合规升级与违规报告

- 来源职业：Compliance Officers, Financial Examiners
- 来源任务：识别需跟进或调查的合规问题；报告法律或法规违规；建议合规行动
- 工作产物：compliance escalation report
- 金融约束：保护隐私；只基于证据描述；无依据问题标记为 open question
- 评测规则：升级适当性、事实纪律、隐私处理、报告格式

## 5. 推荐覆盖规模

本版本广度优先，建议 v1 使用：

- 4 条主 workflow。
- 9 个核心 O*NET 职业。
- 每个 workflow 4-6 个原子任务族。
- 总计约 20-24 个原子任务族。
- 每个任务族合成 10-20 条样本。
- 总样本量约 250-500 条。

推荐分布：

| Workflow | 建议样本占比 | 主要能力 |
| --- | ---: | --- |
| Intake & Profiling | 20% | 信息抽取、缺失识别、客户画像、权限边界 |
| Credit & Underwriting | 30% | 多文档推理、计算、政策阈值、审批升级 |
| Investment & Trading Decision | 25% | 投资研究、交易指令、适当性、模型解释 |
| Risk & Compliance Review | 25% | 风险识别、压力测试、合规审查、审计发现 |

## 6. 约束类型库

这些约束可以跨 workflow 复用：

- 只使用给定 context，不使用外部事实。
- 每个结论必须引用证据。
- 区分事实、假设、推断和建议。
- 数值计算必须展示公式或中间结果。
- 缺失或冲突信息必须标记，不得自行补全。
- 客户话术不得保证收益、批准、税务结果或法律结论。
- 超出权限、受限产品、重大合规问题必须升级。
- 输出必须遵循指定工作产物格式。
- 隐私信息在摘要中必须最小化披露。
- 不得把模型输出包装成确定性投资建议。

## 7. 评测规则类型库

这些评测规则可以跨 workflow 复用：

- 信息抽取正确性。
- 缺失项识别。
- 证据 grounding。
- 数值计算准确性。
- 政策/规则匹配。
- 权限边界遵循。
- 风险分类准确性。
- 严重性校准。
- 升级/拒绝判断。
- 客户话术合规。
- 输出格式遵循。
- 不确定性处理。
- 压缩忠实度。

## 8. 来源说明

O*NET 原始职业描述和任务来自 O*NET OnLine 官方职业页面：

- Credit Analysts, 13-2041.00
- Loan Officers, 13-2072.00
- Personal Financial Advisors, 13-2052.00
- Compliance Officers, 13-1041.00
- Financial Managers, 11-3031.00
- Financial and Investment Analysts, 13-2051.00
- Securities, Commodities, and Financial Services Sales Agents, 41-3031.00
- Financial Quantitative Analysts, 13-2099.01
- Financial Risk Specialists, 13-2054.00
- Financial Examiners, 13-2061.00
- Accountants and Auditors, 13-2011.00
