# 金融指令遵循 Benchmark：任务体系

日期：2026-06-04

## 0. 设计定位

这个 benchmark 不建议直接把 O*NET 的原始任务句子作为最终评测任务。更合适的做法是：把 O*NET 当成“职业池”和“任务种子层”，再围绕真实金融工作流重写成可合成、可评分、可扩展的任务体系。

核心链条：

```text
职业 -> 任务 -> 工作产物 -> 金融约束 -> 评测规则
```

合成链条：

```text
任务 -> context -> query -> constraint -> protocol
```

最终任务单元：

```text
职业 x 原子工作流任务 x 工作产物
```

一个好的原子工作流任务需要足够具体，能自然决定 context、query、constraint 和评分规则；同时也要足够抽象，能支持多个合成样本，而不是只对应一道题。

## 1. 从 O*NET 照搬/压缩得到的职业和任务种子体系

这一层保留 O*NET 的职业结构，并把 O*NET 原始任务压缩成适合 benchmark 设计的 seed task groups。它不是最终任务体系，而是后续重写的来源。

### 1.1 核心职业

#### Credit Analysts, 13-2041.00

O*NET 职责重点：分析信用数据和财务报表，判断贷款风险，并准备决策报告。

任务种子：

- 分析信用数据和财务报表，评估贷款风险。
- 结合信用分析和贷款请求摘要，完成贷款申请材料。
- 生成财务比率，用于评估客户财务状态。
- 准备描述信用风险的报告。
- 分析借款人盈利能力驱动因素，例如收入增长、管理质量、市场份额。
- 将流动性、盈利能力、信用历史与行业或地区同类对象比较。
- 与客户沟通，解决投诉，并核验信用或金融交易。

#### Loan Officers, 13-2072.00

O*NET 职责重点：评估、授权或建议批准商业贷款、房地产贷款或信用贷款；向借款人说明财务状态和还款方式。

任务种子：

- 与申请人会面，收集贷款申请信息，并回答流程问题。
- 分析财务状态、信用状况和抵押物/房产评估，判断贷款可行性。
- 在权限范围内批准贷款，或将例外情况提交管理层。
- 向客户解释贷款类型、信用选项和服务条款。
- 将申请提交给信用分析师进行核验和建议。
- 审核贷款协议的完整性和政策准确性。
- 审核并更新信用和贷款文件。
- 获取信用历史、企业财务报表和其他财务信息。
- 与客户讨论财务目标和还款路径。
- 计算还款计划。
- 与申请人、债权人或承保方沟通，解决申请问题。
- 联系逾期借款人，协商还款计划。

#### Financial and Investment Analysts, 13-2051.00

O*NET 职责重点：对投资项目或机构财务数据进行定量分析，包括企业估值。

任务种子：

- 就融资规模、资金来源和融资时点向客户提供建议。
- 分析困境公司表现，并提出补救措施。
- 评估公司作为投资标的的质量。
- 与律师、会计师、银行家、公关专业人员协作。
- 与客户一起进行债务重组、债务再融资或新增债务融资。
- 制作面向客户的方案展示材料。
- 使用财务模型分析交易或资本结构影响。
- 评估行业内证券质量。
- 根据资本需求和市场条件评估融资方案。
- 分析财务信息，预测企业、行业或经济状况。
- 解读价格、收益率、稳定性、投资风险趋势和经济影响。
- 从多个信息源监控行业、公司和经济发展。
- 进行证券估值或定价。
- 准备交易或 deal execution 材料。
- 准备投资行动计划和建议。
- 展示关于经济趋势、公司或行业的报告。

#### Financial Risk Specialists, 13-2054.00

O*NET 职责重点：分析和衡量信用风险、市场风险等对资产、盈利能力或组织财务状态的威胁。

任务种子：

- 分析可能影响资产、收益或组织成功的风险区域。
- 分析新法规对风险暴露的影响。
- 使用统计分析量化风险。
- 与交易员沟通策略或持仓中的风险。
- 查阅金融文献，获取模型和统计技术。
- 开发或实施风险评估模型和方法。
- 设计严重市场事件下的情景分析。
- 维护风险管理系统的数据质量。
- 从内部或外部来源收集风险相关数据。
- 识别潜在投资中的关键风险和缓释因素。
- 解读价格、收益率、稳定性、未来风险趋势和经济影响。
- 与客户会面，回答风险暴露或 VaR 相关问题。
- 产出报告或展示材料，解释风险头寸并建议调整。
- 建议控制或降低风险的方法。
- 审查或起草发行文件中的风险披露。
- 跟踪、衡量或报告交易证券的市场风险。

#### Financial Examiners, 13-2061.00

O*NET 职责重点：检查金融机构，确认合规性、安全稳健性、交易合法性和偿付能力。

任务种子：

- 主持与董事、高级管理层、法律顾问、会计师和咨询顾问的会议，收集信息并讨论发现。
- 建议实现法律合规或维持机构偿付能力的行动。
- 准备关于安全稳健性、合规性、建议补救措施的报告、附件和支持性表格。
- 处理金融完整性问题，包括贷款组合、资本、收益和问题账户。
- 调查金融机构活动，确认法律合规、交易合法性和偿付能力。
- 审查资产负债表、收入/费用账户和贷款文件。
- 审查内部和外部审计报告，判断审计范围是否充分、是否存在控制缺陷。
- 审查会议纪要，追踪管理授权。
- 建立符合新法规的政策和程序指南。
- 解读新的或修订后的法律、法规、政策和程序。
- 提供监管合规培训。
- 评估被检查机构使用的数据处理应用。
- 审查并购、新设机构、美联储会员资格或证券注册申请。
- 检查现金储备、抵押品和银行持有证券的内部控制程序。

#### Securities, Commodities, and Financial Services Sales Agents, 41-3031.00

O*NET 职责重点：买卖证券或商品，提供金融服务，并就市场条件向客户提供建议。

任务种子：

- 对买卖证券提出报价或出价。
- 监控市场或持仓。
- 在适合客户的价格水平上达成买卖价格。
- 保持准确的交易记录。
- 代表交易商或客户买卖证券或其他金融工具。
- 为客户请求的交易完成销售订单票据。
- 报告持仓或交易结果。
- 提供价格报价和发行人财务状况信息。
- 就证券、商品、市场条件和金融服务向客户提供建议。
- 根据客户需求定制金融产品或服务。
- 与同事共享销售或市场信息。
- 向客户解释产品或服务的技术信息。

### 1.2 补充职业

#### Personal Financial Advisors, 13-2052.00

任务种子：

- 访谈客户，了解收入、支出、保险、税务状态、目标和风险承受能力。
- 分析客户财务信息并确定策略。
- 回答客户关于计划细节和策略的问题。
- 在生活事件、市场变化或业绩变化时复核账户和计划。
- 管理投资组合，并保持计划更新。
- 推荐现金管理、保险、投资或相关策略。
- 推荐金融产品。
- 实施建议，或将客户转介给合适人员实施。
- 联系客户，识别财务状态变化。
- 准备或解释投资表现报告、文件摘要或收入预测。
- 解释顾问职责和服务范围。
- 调查投资机会是否符合客户计划。
- 指导客户收集银行、税务、保险、养老金和遗产文件。
- 监控市场趋势，使客户计划保持响应性。
- 与律师、会计师、信托官员或银行家会面，理解客户情况。
- 设计债务清偿优先级和时间表。

#### Accountants and Auditors, 13-2011.00

任务种子：

- 准备详细审计发现报告。
- 向管理层报告资产利用和审计结果，并提出运营或财务建议。
- 发现控制缺陷、重复劳动、浪费、欺诈或不合规。
- 检查账簿和会计系统是否符合程序并有效运行。
- 确定审计范围并监督审计。
- 与公司管理人员讨论财务和监管事项。
- 评估财务和信息系统，并建议可靠性或数据完整性控制。
- 检查现金、应收账款、应付账款、证券和已注销支票，以确认记录。
- 审查记录并访谈员工，确认交易记录和合规情况。
- 分析会计记录、财务报表和报告，判断准确性和准则符合性。
- 准备调整分录。
- 审查账户差异并进行调节。
- 将分录分配到适当账户。
- 将库存与日记账和总账分录核对。
- 分析运营、趋势、成本、收入、承诺和义务，用于预测或建议。
- 开发、修改并记录会计系统。
- 在相关场景中计算税额并准备税表。

#### Tax Preparers, 13-2082.00

任务种子：

- 根据说明和税表计算应缴或多缴税额，并填写表格。
- 应用适当的调整、扣除和税收抵免。
- 向纳税人提供正确填表所需信息。
- 访谈客户，了解应税收入、可扣除费用和免税/抵免项目。
- 为个人或小企业准备或协助准备从简单到复杂的税表。
- 审查财务记录和支出文件，确定所需税表。
- 核验数据输入和合计数，发现算术、录入或程序错误。
- 解释联邦和州税法。
- 回答客户问题，并提供未来税务规划建议。
- 对非典型税表查阅税法手册或公告。

#### Financial Quantitative Analysts, 13-2099.01

任务种子：

- 将数学或统计技术应用于衍生品、交易、风险或监管等金融问题。
- 开发用于组合构建、优化、绩效衡量、归因、P&L 或定价的分析工具。
- 解读金融分析结果。
- 使用统计、定量或计量经济方法构建分析能力或模型库。
- 定义模型规格或数据收集方法。
- 产出金融研究结果的书面摘要。
- 维护或修改金融分析模型。
- 在估值或数据问题上支持研究员或交易员。
- 使用独立模型核验分析系统结果。
- 根据用户需求和范围测试分析软件。
- 就交易策略、市场动态或系统表现进行沟通。
- 研究新的金融产品或分析方法。
- 跟踪交易系统运营指标。
- 为软件开发人员准备需求文档。

#### Financial Managers, 11-3031.00

任务种子：

- 维护个人或企业客户关系，并协助解决问题。
- 监督现金或金融工具流动。
- 协调银行、经纪、风险、保险或信贷部门活动。
- 评估成本数据以制定预算。
- 建立资产、记录、抵押品或证券的保管和控制程序。
- 与投资者沟通，提供信息或筹集资本。
- 分析企业当前或未来财务状态。
- 批准、拒绝或协调批准信用额度或贷款。
- 准备财务或监管报告。
- 审查、评估或处理贷款申请。
- 评估财务报告系统、会计/收款程序或投资活动。
- 为管理层准备运营或风险报告。
- 审查催收和未偿余额报告。
- 审查证券交易报告或价目表，分析市场条件。

#### Compliance Officers, 13-1041.00

任务种子：

- 评估申请、记录或文件中的资格或责任问题。
- 向个人或群体解释法规。
- 准备活动、评估、建议或决策报告。
- 向适当机构报告法律或法规违规。
- 访谈官员、专家或申请人以澄清事实。
- 准备关于决策或申诉流程的通信。
- 识别需要跟进或调查的合规问题。
- 跟踪行业变化、趋势或最佳实践。
- 协助内部或外部审计人员进行合规审查。
- 核验公司和监管政策程序是否已记录、实施并传达。

## 2. 重写后的金融工作流原子任务类型

这一层把 O*NET 种子任务改写成可直接用于 benchmark 的原子任务类型。每个任务类型都有稳定工作产物、自然的 context 来源，以及可测的指令遵循难点。

### 2.1 信贷与贷款工作流

#### CA-01 借款人信用质量评估

- 职业：Credit Analyst
- 工作产物：内部 credit memo
- Context：贷款申请、财务报表、信用报告、银行流水、抵押物评估、贷款政策
- Query：建议批准、拒绝或升级
- 约束：引用证据；计算必要比率；只使用给定数据；标记缺失或不一致信息
- 评测：比率正确性、证据 grounding、政策遵循、升级判断、格式遵循

#### CA-02 财务比率与 covenant 审查

- 职业：Credit Analyst
- 工作产物：比率表和 covenant 例外说明
- Context：借款人报表、现有 covenant、同业 benchmark、政策阈值
- Query：计算比率并识别 covenant 或政策阈值违约
- 约束：展示公式；区分会计事实和推断风险；不得编造不可得科目
- 评测：计算准确性、违约识别、证据引用、不确定性处理

#### CA-03 贷款盈利性与风险摘要

- 职业：Credit Analyst
- 工作产物：风险调整后的贷款盈利性摘要
- Context：拟议贷款条款、借款人财务、预期费用、抵押品、可比借款人、信贷政策
- Query：总结预期盈利性和主要风险驱动因素
- 约束：区分盈利性、偿债能力和抵押品质量
- 评测：分解是否正确、风险排序、是否忠实使用 context

#### CA-04 同业比较信用审查

- 职业：Credit Analyst
- 工作产物：同业比较附录
- Context：借款人指标、行业/地区同业表、历史表现
- Query：比较流动性、盈利能力、杠杆和信用历史
- 约束：引用所用 percentile 或 benchmark；避免无依据因果判断
- 评测：比较正确性、相关证据选择、解释简洁性

#### LO-01 贷款 intake 完整性检查

- 职业：Loan Officer
- 工作产物：缺失文件清单
- Context：借款人申请、已上传文件、产品要求、身份/KYC 清单
- Query：判断材料包是否可以进入 underwriting
- 约束：只提出必要追问；区分必需缺失项和可选缺失项
- 评测：完整性、优先级、无不必要请求、格式遵循

#### LO-02 贷款资格与转交决策

- 职业：Loan Officer
- 工作产物：一线资格判断
- Context：申请材料、借款人财务、房产/抵押物评估、审批权限政策、例外政策
- Query：在权限内批准、转交或拒绝
- 约束：遵守权限边界；不得承诺批准；解释下一步
- 评测：权限边界遵循、决策正确性、客户安全解释

#### LO-03 贷款条款解释

- 职业：Loan Officer
- 工作产物：面向客户的解释
- Context：贷款选项、APR/费用、摊还表、借款人目标、披露要求
- Query：解释可选贷款方案及 trade-off
- 约束：使用通俗语言；包含必要披露；不得使用保证结果话术
- 评测：清晰度、披露完整性、无误导表述、指令格式

#### LO-04 逾期账户还款计划

- 职业：Loan Officer
- 工作产物：还款计划建议和内部记录
- Context：逾期历史、客户现金流信息、困难/催收政策、既往沟通
- Query：提出可行还款选项或升级处理
- 约束：避免超出政策的威胁性语言；保留客户事实；识别人工复核需求
- 评测：政策遵循、可行性、语气合规、证据使用

### 2.2 投资研究与资本市场工作流

#### FIA-01 投资研究 memo

- 职业：Financial and Investment Analyst
- 工作产物：investment memo
- Context：公司 filings、财务报表、市场数据、行业报告节选、新闻、估值假设
- Query：产出投资 thesis、风险、估值观点和推荐类别
- 约束：区分事实、假设和建议；引用来源片段；不得使用外部事实
- 评测：证据 grounding、thesis 连贯性、风险完整性、格式遵循

#### FIA-02 困境公司补救方案审查

- 职业：Financial and Investment Analyst
- 工作产物：turnaround / restructuring options memo
- Context：困境财务数据、债务排期、现金流预测、covenant notice、运营指标
- Query：识别困境原因并推荐补救措施
- 约束：区分流动性问题和偿付能力问题；标记假设；避免法律确定性表述
- 评测：诊断准确性、方案适配性、不确定性处理

#### FIA-03 融资结构与资本方案分析

- 职业：Financial and Investment Analyst
- 工作产物：融资结构建议
- Context：资本需求、市场条件、债务/股权选项、股东约束、评级考虑
- Query：推荐融资金额、资金来源和融资时点
- 约束：比较替代方案；说明 trade-off；不得忽视客户已给约束
- 评测：替代方案分析、约束满足、市场条件使用

#### FIA-04 证券估值与定价

- 职业：Financial and Investment Analyst
- 工作产物：估值 worksheet 摘要
- Context：价格/收益率数据、可比证券、现金流假设、折现率指引
- Query：对证券估值或定价，并解释敏感性
- 约束：展示关键假设；识别数据缺口；保持数值一致
- 评测：数值正确性、假设透明度、敏感性推理

#### FIA-05 交易执行材料检查

- 职业：Financial and Investment Analyst
- 工作产物：交易材料清单
- Context：展示材料草稿、term sheet、尽调清单、政策清单、客户目标
- Query：识别执行前缺失或不一致的材料
- 约束：区分 blocking 与 nonblocking 问题；引用文件位置
- 评测：问题识别、优先级、证据 grounding

#### SCS-01 交易指令解析

- 职业：Securities/Commodities/Financial Services Sales Agent
- 工作产物：结构化 order ticket
- Context：客户消息、账户限制、产品列表、价格报价、交易政策
- Query：抽取证券、方向、数量、订单类型、限价、有效期、账户和缺失字段
- 约束：不得执行歧义订单；标记受限产品
- 评测：字段抽取、歧义识别、政策遵循

#### SCS-02 交易前适当性与合规检查

- 职业：Securities/Commodities/Financial Services Sales Agent
- 工作产物：pre-trade review note
- Context：客户画像、风险承受能力、持仓、拟交易产品、集中度限制、披露要求
- Query：判断交易可继续、需要披露还是需要升级
- 约束：不得推荐不适当产品；引用客户画像冲突
- 评测：适当性推理、升级判断、避免禁止性承诺

#### SCS-03 持仓和交易结果报告

- 职业：Securities/Commodities/Financial Services Sales Agent
- 工作产物：position / trading result report
- Context：已执行交易、持仓、市场价格、P&L、费用、benchmark
- Query：总结当前持仓和交易结果
- 约束：调节总数；区分已实现和未实现结果；包含必要 caveat
- 评测：调节准确性、分类正确性、简洁报告

### 2.3 风险管理工作流

#### FRS-01 市场与信用风险识别

- 职业：Financial Risk Specialist
- 工作产物：risk register
- Context：组合持仓、交易对手暴露、评级、抵押品、宏观情景、政策 taxonomy
- Query：识别关键风险和缓释因素
- 约束：分类风险类型；引用证据；区分已观察暴露和推断脆弱性
- 评测：风险覆盖、taxonomy 准确性、证据 grounding

#### FRS-02 情景分析与压力测试摘要

- 职业：Financial Risk Specialist
- 工作产物：stress-test summary
- Context：持仓、敏感性、情景定义、历史冲击、流动性假设
- Query：估计严重市场情景下的影响并总结驱动因素
- 约束：只使用给定情景定义；标记非线性或缺失敏感性
- 评测：计算、情景遵循、驱动因素解释

#### FRS-03 风险模型方法论审查

- 职业：Financial Risk Specialist
- 工作产物：model methodology critique
- Context：模型说明、假设、验证结果、数据 lineage、风险政策
- Query：识别模型限制并推荐控制措施
- 约束：区分验证证据和猜测；不得夸大模型可靠性
- 评测：限制识别、控制相关性、不确定性处理

#### FRS-04 风险披露审查

- 职业：Financial Risk Specialist
- 工作产物：risk disclosure redline notes
- Context：发行文件节选、组合策略、已知风险、法律/合规指引
- Query：审查披露是否覆盖重大风险
- 约束：标记遗漏；避免把法律意见写成最终结论；引用缺失证据
- 评测：重大性判断、遗漏识别、安全边界

#### FRS-05 管理层风险报告

- 职业：Financial Risk Specialist
- 工作产物：management risk briefing
- Context：风险指标、历史报告、limit breach、事件记录、整改状态
- Query：产出带行动项的 executive summary
- 约束：优先高严重性项目；如 context 中存在 owner/date 字段则纳入
- 评测：优先级、可行动性、压缩忠实度

### 2.4 金融检查与合规工作流

#### FE-01 金融机构检查计划

- 职业：Financial Examiner
- 工作产物：exam plan 和文件请求清单
- Context：机构画像、历史检查发现、审计报告、监管范围、风险指标
- Query：规划检查并请求证据
- 约束：请求需匹配检查范围；避免无关 fishing；识别高风险重点
- 评测：范围遵循、风险导向计划、请求精确性

#### FE-02 安全稳健性报告

- 职业：Financial Examiner
- 工作产物：检查报告章节
- Context：资产负债表、收入/费用账户、贷款文件、资本数据、流动性报告
- Query：评估 safety and soundness，并建议补救措施
- 约束：引用证据；区分合规、偿付能力和运营问题
- 评测：证据 grounding、问题分类、补救适配性

#### FE-03 内部控制缺陷审查

- 职业：Financial Examiner
- 工作产物：control weakness memo
- Context：审计报告、现金储备、抵押品记录、证券持仓、流程叙述
- Query：识别控制缺陷和严重性
- 约束：将每项发现映射到证据和控制目标
- 评测：发现有效性、严重性校准、证据映射

#### FE-04 监管变化影响分析

- 职业：Financial Examiner / Compliance Officer
- 工作产物：regulation impact memo
- Context：新规则节选、现行政策、流程图、受影响产品、培训材料
- Query：判断需要更新的政策或程序
- 约束：只引用规则章节标识；避免外部法律解释
- 评测：规则映射、影响完整性、行动具体性

#### CO-01 合规问题分诊

- 职业：Compliance Officer
- 工作产物：compliance triage log
- Context：alerts、客户/账户记录、政策节选、历史决定、沟通记录
- Query：识别需要跟进或调查的问题
- 约束：分类严重性；引用触发证据；摘要中保护隐私
- 评测：问题识别、严重性准确性、隐私合规

#### CO-02 政策实施核验

- 职业：Compliance Officer
- 工作产物：policy implementation checklist
- Context：政策、程序、培训记录、系统截图/说明、control owner attestation
- Query：核验政策是否已记录、实施并传达
- 约束：标记 unknown；区分文件存在和运行有效性
- 评测：清单正确性、保守判断、证据使用

#### CO-03 违规报告草稿

- 职业：Compliance Officer
- 工作产物：violation escalation report
- Context：疑似违规事实、政策、通信、整改历史
- Query：准备提交给适当机构或内部委员会的报告
- 约束：避免无依据指控；包含证据和开放问题
- 评测：事实纪律、升级适当性、语气和格式

### 2.5 财富管理、税务、会计与管理工作流

#### PFA-01 客户财务画像构建

- 职业：Personal Financial Advisor
- 工作产物：client financial profile
- Context：访谈记录、账户报表、保险、税务状态、目标、风险承受能力、遗产文件
- Query：编制客户画像并识别缺失信息
- 约束：区分已核实数据和客户陈述目标；暂不做产品推荐
- 评测：抽取完整性、缺失项识别、边界遵循

#### PFA-02 财务计划复核

- 职业：Personal Financial Advisor
- 工作产物：plan reassessment note
- Context：现有计划、组合表现、生活事件、市场变化、现金流更新
- Query：判断是否需要重新评估或再平衡
- 约束：解释触发因素；避免保证业绩；标记税务/顾问协同需求
- 评测：触发识别、建议谨慎性、context 使用

#### PFA-03 债务清偿计划

- 职业：Personal Financial Advisor
- 工作产物：debt payoff schedule
- Context：负债、利率、最低还款额、现金流约束、客户偏好
- Query：确定清偿优先级并估计时间线
- 约束：遵守 emergency fund 约束；展示 avalanche/snowball 方法 trade-off
- 评测：还款数学、约束遵循、解释清晰度

#### AA-01 审计发现识别

- 职业：Accountant/Auditor
- 工作产物：audit findings table
- Context：会计记录、控制叙述、发票、审批、银行调节表、政策
- Query：识别控制缺陷、重复劳动、欺诈迹象或不合规
- 约束：引用证据；区分 finding、risk 和 recommendation
- 评测：发现正确性、证据、严重性、不过度指控

#### AA-02 财务报表一致性检查

- 职业：Accountant/Auditor
- 工作产物：reconciliation memo
- Context：试算表、财务报表、日记账分录、总账摘录、支持性明细
- Query：寻找差异并提出调整分录
- 约束：展示借贷方向；不得改变源事实；标记未解决项目
- 评测：会计逻辑、算术、格式、不确定性

#### AA-03 内部控制建议

- 职业：Accountant/Auditor
- 工作产物：control recommendation memo
- Context：系统说明、访问日志、职责分离矩阵、审计发现
- Query：推荐提高可靠性和数据完整性的控制措施
- 约束：将控制映射到风险；区分预防性、侦测性和纠正性控制
- 评测：控制-风险匹配、分类、可操作性

#### TP-01 税务申报文件审查

- 职业：Tax Preparer
- 工作产物：tax document checklist
- Context：客户 intake、W-2/1099 表、业务费用、上年申报、税表说明
- Query：判断所需表格和缺失记录
- 约束：使用给定 tax year 规则；只提出必要追问
- 评测：表格选择、缺失项识别、无幻觉规则

#### TP-02 扣除与抵免资格判断

- 职业：Tax Preparer
- 工作产物：eligibility table
- Context：收入、费用、被抚养人、deduction/credit 政策、收据
- Query：识别允许的扣除/抵免和被拒项目
- 约束：引用规则条件；避免激进且无依据的税务立场
- 评测：资格准确性、证据、保守处理

#### TP-03 税务错误复核

- 职业：Tax Preparer
- 工作产物：data-entry and arithmetic error report
- Context：申报草稿、源文件、税表、preparer notes
- Query：发现算术、录入或程序错误
- 约束：报告 line item、源证据和修正建议
- 评测：错误识别、修正准确性、可追溯性

#### FQA-01 模型结果解释

- 职业：Financial Quantitative Analyst
- 工作产物：model result interpretation note
- Context：模型输出、假设、输入数据摘要、验证指标、交易员问题
- Query：解释结果和限制
- 约束：区分模型输出和投资建议；标记验证缺口
- 评测：解释准确性、限制意识、边界遵循

#### FQA-02 独立模型核验

- 职业：Financial Quantitative Analyst
- 工作产物：independent verification report
- Context：生产模型输出、独立检查模型、样本数据、差异日志
- Query：核验结果是否一致并解释差异
- 约束：量化差异；分类严重性；避免重写模型假设
- 评测：差异识别、数值比较、严重性判断

#### FQA-03 分析工具需求文档

- 职业：Financial Quantitative Analyst
- 工作产物：给软件开发者的 requirements brief
- Context：交易员/研究员请求、当前工具限制、数据字段、合规约束
- Query：为新的或改进后的分析应用起草需求
- 约束：包含用户需求、范围、输入、输出、验收测试
- 评测：完整性、可测试性、范围纪律

#### FM-01 现金与金融工具监督

- 职业：Financial Manager
- 工作产物：cash / instrument oversight report
- Context：现金头寸、金融工具库存、流动性政策、结算日历、例外事项
- Query：总结资金流、例外和行动项
- 约束：调节总数；识别时间敏感事项；区分现金和证券
- 评测：调节、例外处理、可行动性

#### FM-02 预算与成本规划

- 职业：Financial Manager
- 工作产物：budget planning memo
- Context：成本数据、预测、部门请求、差异历史、董事会约束
- Query：制定预算或建议预算调整
- 约束：引用成本驱动因素；遵守 caps；区分固定成本和可变成本
- 评测：预算数学、约束遵循、理由

#### FM-03 监管与董事会报告

- 职业：Financial Manager
- 工作产物：regulatory / board report draft
- Context：财务结果、风险报告、董事会要求、监管模板、历史提交版本
- Query：准备报告章节并识别缺失输入
- 约束：遵循模板；不得做无依据 certification；标记不可得证据
- 评测：模板遵循、完整性、保守 certification

## 3. 最终可直接使用的完整任务体系

最终体系按真实金融生命周期组织。每个 workflow 都包含相关职业、原子任务、工作产物、典型长 context 来源和评测目标。

### A. 客户或交易对手 intake

#### A1. Intake 材料完整性

- 主要职业：Loan Officer, Personal Financial Advisor, Tax Preparer, Compliance Officer
- 原子任务：LO-01, PFA-01, TP-01, CO-01
- 工作产物：缺失文件清单、客户画像、税务文件清单、合规分诊日志
- Context 来源：申请表、客户消息、上传文件、历史账户记录、KYC 清单、政策节选
- 金融约束：隐私、完整性、权限边界、不得过早给出建议
- 评测规则：正确抽取、缺失字段识别、最小化追问、不得编造数据

#### A2. 客户目标与风险画像构建

- 主要职业：Personal Financial Advisor, Loan Officer, Securities Agent
- 原子任务：PFA-01, LO-03, SCS-02
- 工作产物：风险画像、客户解释、适当性说明
- Context 来源：访谈记录、财务目标、风险承受能力、组合、收入/支出数据、产品披露
- 金融约束：风险适当性、通俗语言、不得保证收益、必要披露
- 评测规则：画像忠实度、适当性冲突识别、合规语气

### B. 信贷与承销

#### B1. 借款人风险评估

- 主要职业：Credit Analyst, Loan Officer, Financial Manager
- 原子任务：CA-01, CA-02, LO-02, FM-03
- 工作产物：credit memo、比率表、资格判断、审批升级说明
- Context 来源：贷款申请、财务报表、信用报告、抵押品评估、政策权限、covenant schedules
- 金融约束：比率公式、贷款权限、证据引用、缺失数据处理
- 评测规则：数值准确性、政策遵循、决策适当性、升级正确性

#### B2. 贷款经济性与还款

- 主要职业：Credit Analyst, Loan Officer, Personal Financial Advisor
- 原子任务：CA-03, LO-03, LO-04, PFA-03
- 工作产物：盈利性摘要、还款表、客户解释、逾期计划
- Context 来源：贷款条款、费用、利率、现金流、逾期历史、困难政策
- 金融约束：不得误导条款、不得承诺批准、催收语气边界
- 评测规则：摊还/还款数学、政策遵循、语气安全、trade-off 清晰

### C. 投资研究与交易工作

#### C1. 投资分析

- 主要职业：Financial and Investment Analyst, Financial Quantitative Analyst, Financial Risk Specialist
- 原子任务：FIA-01, FIA-04, FQA-01, FRS-01
- 工作产物：investment memo、估值摘要、模型解释、risk register
- Context 来源：filings、财务报表、市场数据、行业报告、模型输出、风险指标
- 金融约束：事实 vs 假设 vs 建议、不得使用外部事实、敏感性披露
- 评测规则：证据 grounding、估值一致性、假设清晰度、风险完整性

#### C2. 融资、资本结构与重组

- 主要职业：Financial and Investment Analyst, Financial Manager
- 原子任务：FIA-02, FIA-03, FIA-05, FM-03
- 工作产物：重组 memo、融资方案建议、deal checklist、董事会报告
- Context 来源：债务排期、covenant notices、资本需求、市场条件、term sheets、尽调清单
- 金融约束：区分流动性和偿付能力、尊重客户约束、分类 blocking issue
- 评测规则：补救适配性、替代方案比较、问题优先级、格式遵循

### D. 交易与经纪运营

#### D1. 订单捕获与交易前审查

- 主要职业：Securities/Commodities/Financial Services Sales Agent, Compliance Officer, Financial Risk Specialist
- 原子任务：SCS-01, SCS-02, CO-01, FRS-01
- 工作产物：order ticket、pre-trade review note、合规 alert、风险说明
- Context 来源：客户订单消息、账户限制、持仓、风险画像、产品披露、市场报价
- 金融约束：歧义订单阻断、适当性、集中度限制、受限产品
- 评测规则：结构化抽取、缺失字段识别、适当性分类、拒绝/升级

#### D2. 持仓、P&L 与交易结果

- 主要职业：Securities Agent, Financial Quantitative Analyst, Financial Manager
- 原子任务：SCS-03, FQA-02, FM-01
- 工作产物：position report、independent verification report、cash/instrument report
- Context 来源：已执行交易、持仓、价格、费用、模型输出、结算日历
- 金融约束：区分 realized vs unrealized、调节、时间戳敏感性
- 评测规则：算术准确性、分类、差异识别、简洁报告

### E. 风险管理

#### E1. 风险识别与监控

- 主要职业：Financial Risk Specialist, Financial Manager, Credit Analyst
- 原子任务：FRS-01, FRS-05, CA-04, FM-01
- 工作产物：risk register、管理层 briefing、同业比较附录、例外报告
- Context 来源：组合、交易对手、信用指标、limit reports、抵押品、历史风险报告
- 金融约束：风险 taxonomy、严重性评分、证据引用、owner/action tracking
- 评测规则：风险覆盖、严重性校准、缓释相关性、压缩忠实度

#### E2. 压力测试与模型治理

- 主要职业：Financial Risk Specialist, Financial Quantitative Analyst
- 原子任务：FRS-02, FRS-03, FQA-01, FQA-02
- 工作产物：stress-test summary、methodology review、模型解释、verification report
- Context 来源：模型假设、情景定义、持仓、敏感性、验证日志、差异表
- 金融约束：只使用给定情景、标记缺失敏感性、不得夸大可靠性
- 评测规则：情景遵循、定量正确性、限制识别、不确定性处理

### F. 合规、检查与审计

#### F1. 金融机构检查

- 主要职业：Financial Examiner, Compliance Officer, Accountant/Auditor
- 原子任务：FE-01, FE-02, FE-03, AA-01
- 工作产物：exam plan、safety-and-soundness report、control weakness memo、audit findings table
- Context 来源：资产负债表、收入/费用账户、贷款文件、审计报告、会议纪要、抵押品记录
- 金融约束：范围纪律、法律/监管映射、证据支撑的发现
- 评测规则：范围遵循、问题分类、补救适配性、严重性校准

#### F2. 监管变化与政策实施

- 主要职业：Financial Examiner, Compliance Officer, Financial Manager
- 原子任务：FE-04, CO-02, CO-03, FM-03
- 工作产物：regulation impact memo、implementation checklist、violation escalation report、regulatory report
- Context 来源：新规则节选、现有政策、培训记录、流程图、疑似违规事实、董事会模板
- 金融约束：不得做无依据法律结论、区分已记录控制和运行中控制、隐私
- 评测规则：规则映射、实施证据、升级适当性、保守语言

#### F3. 会计与财务报表复核

- 主要职业：Accountant/Auditor, Financial Manager, Tax Preparer
- 原子任务：AA-01, AA-02, AA-03, TP-03
- 工作产物：审计发现、reconciliation memo、control recommendation、tax error report
- Context 来源：总账、试算表、日记账分录、调节表、发票、税表、源文件
- 金融约束：会计准则/程序、借贷完整性、不得修改源事实
- 评测规则：会计正确性、差异识别、可追溯性、调整逻辑

### G. 税务准备与规划

#### G1. 税表准备与资格判断

- 主要职业：Tax Preparer, Accountant/Auditor
- 原子任务：TP-01, TP-02, TP-03
- 工作产物：税务文件清单、扣除/抵免表、错误报告
- Context 来源：客户 intake、收入表、费用记录、上年申报、税表说明、州/联邦规则节选
- 金融约束：使用给定 tax-year 规则、保守资格判断、不得采取激进且无依据立场
- 评测规则：表格选择、资格准确性、算术、缺失证据处理

#### G2. 客户税务解释

- 主要职业：Tax Preparer, Personal Financial Advisor
- 原子任务：TP-02, TP-03, PFA-02
- 工作产物：面向客户的税务解释、planning note
- Context 来源：完成版申报草稿、被拒扣除项、规划假设、未来收入/费用变化
- 金融约束：通俗语言、不得保证税务结果、复杂法律问题需转介
- 评测规则：清晰度、规则引用、风险 caveat、边界适当性

### H. 管理报告与治理

#### H1. 高管财务简报

- 主要职业：Financial Manager, Financial Risk Specialist, Financial and Investment Analyst
- 原子任务：FM-01, FM-02, FM-03, FRS-05, FIA-03
- 工作产物：董事会/监管报告、预算 memo、管理层风险 briefing、融资建议
- Context 来源：财务结果、成本数据、风险指标、历史报告、董事会约束、投资者沟通
- 金融约束：模板遵循、不得无依据 certification、按重大性排序
- 评测规则：压缩忠实度、重大性、数值一致性、可行动性

#### H2. 分析系统与需求治理

- 主要职业：Financial Quantitative Analyst, Financial Examiner, Compliance Officer
- 原子任务：FQA-03, FE-03, CO-02
- 工作产物：analytics requirements brief、control memo、implementation checklist
- Context 来源：用户请求、当前工具输出、数据字典、控制目标、合规约束
- 金融约束：验收测试清晰、范围边界、数据 lineage、控制文档
- 评测规则：需求完整性、可测试性、控制-风险映射、实施证据

## 4. 推荐 v1 覆盖规模

推荐 v1 benchmark：

- 12 个职业。
- 33 个原子任务类型。
- 8 个生命周期 workflow groups。
- 450-700 个 benchmark items。

建议分配：

- 核心职业：70% items。
- 补充职业：30% items。
- 长 context items：至少 50%。
- 多文档 items：至少 40%。
- 计算或调节 items：至少 25%。
- 安全/合规/升级 items：至少 25%。
- 面向客户、带话术约束 items：至少 15%。

## 5. 为什么这个任务体系适合 benchmark 假设

benchmark 假设建议写成：

> 金融工作流经常把长且异构的 context、高风险约束、证据要求、数值核验、角色边界和受监管的输出格式组合在一起。这个组合会系统性增加 instruction following 难度。

关键变量不是 context 长度本身。最强的 benchmark item 应该组合以下因素：

- 多个 context 来源；
- 相关证据分散；
- 存在无关干扰信息；
- 存在冲突或不完整信息；
- 政策约束之间有层级；
- 存在角色或权限边界；
- 需要计算；
- 需要证据引用；
- 有输出格式 protocol；
- 有安全拒绝或升级条件。

## 6. 来源说明

主要来源：

- O*NET OnLine: Credit Analysts, 13-2041.00.
- O*NET OnLine: Loan Officers, 13-2072.00.
- O*NET OnLine: Financial and Investment Analysts, 13-2051.00.
- O*NET OnLine: Financial Risk Specialists, 13-2054.00.
- O*NET OnLine: Financial Examiners, 13-2061.00.
- O*NET OnLine: Securities, Commodities, and Financial Services Sales Agents, 41-3031.00.
- O*NET OnLine: Personal Financial Advisors, 13-2052.00.
- O*NET OnLine: Accountants and Auditors, 13-2011.00.
- O*NET OnLine: Tax Preparers, 13-2082.00.
- O*NET OnLine: Financial Quantitative Analysts, 13-2099.01.
- O*NET OnLine: Financial Managers, 11-3031.00.
- O*NET OnLine: Compliance Officers, 13-1041.00.
