# FinIF Conference Paper Handoff Notes

本文件记录本轮对话中已经确定的论文转接信息，供后续继续写作、修改摘要、Related Work 和实验叙事时使用。核心原则：不要重新发明故事线；除非用户明确要求改逻辑，否则只做局部压缩、润色或结构化表达。

## 1. 当前任务背景

项目路径：`/Users/minimax/Desktop/Projects/FinIF/current`

当前状态：原论文已经基本写完，现在需要改造成会议论文，并优化部分流程与表述。

用户列出的主要待办：

1. 写标题和大纲。
2. 写 abstract。
3. 确定任务分类体系、约束分类体系、合成数据。
4. 继续迭代 FinIF，让大模型评分降到 20 以下，用于更强地区分强模型能力。

## 2. 已固定的核心故事线

后续写摘要、Introduction、Related Work 时必须保持下面的顺序，不要随意调换：

1. 金融是 LLM 落地的重要场景。
2. 金融任务的可靠性不只取决于“答得对”，还取决于是否能满足明确的交付要求。
3. 我们观察到：现有 LLM 在金融任务中的基础指令遵循并不稳定。
4. 这暴露了现有评测的缺口：金融 benchmark 多关注知识、抽取、推理和答案正确性；通用 IF benchmark 缺少金融语境和金融交付约束。
5. 因此提出 FinIF，面向金融场景中的 instruction following。
6. FinIF 的核心是可扩展的 `context-query-constraint` 数据构造管线。
7. FinIF 的评测同时看“是否答对”和“是否按要求交付”：硬约束用 rule-based checker，软约束用 LLM-as-a-judge。
8. 实验表明 FinIF 能揭示强模型的系统性不足，且约束越密集失败越明显。
9. FinIF-Train 的 SFT 结果说明金融 instruction following 是可测、可训练、值得单独优化的能力。

一句话版本：

> FinIF argues that reliable financial LLMs require not only financial correctness, but also stable compliance with domain-specific delivery requirements.

## 3. 用户明确否定或需要避免的表达

以下表达或写法已经被用户指出有问题，后续不要重复使用：

- 不要说金融任务“天然适合”LLM。这个判断太主观，容易被审稿人追问。
- 不要把“金融文本处理”说成金融落地的全部，金融任务不只有文本处理。
- 不要把故事线写成“模型不是不会金融，而是不遵守指令”的强断言；这容易被质疑“它真的会金融吗”。更稳的说法是：失败并不只来自复杂金融知识或推理，很多失败发生在基于给定材料的抽取、整理或简单计算任务中。
- 不要在摘要中堆数据细节，例如 `100 cases / 300 constraints / 2,134 samples`。这些更适合放在 Introduction contribution 或 Dataset section。
- 不要在摘要里重复说 `benchmark and training framework` 后又解释 `benchmark + training dataset`，信息密度低。
- 不要随意调整“观察到模型不稳定”和“现有评测缺口”的顺序；用户要求先讲观察，再讲 gap。
- 不要使用没有逻辑的 `However`。例如从“金融任务有材料、问题和交付要求”直接转到“可靠应用还需要遵守要求”不是转折，而是递进。

## 4. 标题方向

用户偏好的标题方向是问题式短标题，参考：

- `PhyX: Does Your Model Have the "Wits" for Physical Reasoning?`
- `Weight-inherited Distillation for Task-agnostic BERT Compression` 的简洁会议论文风格。

目前推荐标题：

> FinIF: Can Large Language Models Follow Instructions in Financial Tasks?

注意：不要写成 `Financial Instuction`，`Instruction` 拼写必须正确；也不要写成 `the Financial Instruction`。

## 5. Abstract 写作要求

EMNLP/ACL Industry Track 论文摘要通常较短，常见范围约 150-200 words；也有 230 words 以上，但不建议写到 300 words。摘要最好是一段式或两段式都可以，但逻辑要非常清楚。

摘要必须踩到以下点：

1. LLM 被用于金融任务。
2. 金融任务可靠性不仅要求答案正确，还要求满足交付约束。
3. 现有 LLM 在金融任务的显式交付约束上不稳定。
4. 现有评测缺口：金融评测偏正确性，通用 IF 评测缺金融语境。
5. 提出 FinIF。
6. FinIF 使用 `context-query-constraint` 构造。
7. 硬约束 rule-based，软约束 LLM-as-a-judge。
8. 实验显示强模型仍失败；FinIF-Train SFT 能提升能力。

当前未形成用户满意的最终 abstract。后续继续写时，先根据上面的故事线逐句压缩，不要改逻辑。

## 6. Related Work 结构

用户希望 Related Work 两个小标题尽量对称，同时第二节不是“评估 Financial Language Models”，而是评估 LLM 的金融能力。

推荐小标题：

1. `Instruction Following of LLMs`
2. `Financial Capabilities of LLMs`

第一节可以覆盖：

- instruction tuning；
- RLHF / DPO / preference-based alignment 等用于提升 IF 的方法；
- IFEval、FollowBench、InfoBench、CFBench 等通用 IF 评测。

注意：用户自己的训练方法只是 SFT，贡献不是新训练算法。因此 RL 类方法需要轻量提到，但不要展开成训练方法综述。建议定位：这些方法提升通用 instruction following，而 FinIF 与它们正交，关注金融场景中的 IF 数据、评测和可训练性验证。

第二节可以覆盖：

- 金融情感分析、信息抽取、问答、数值推理、报告分析、风险评估、投研相关决策支持等；
- 金融 NLP benchmark 和 LLM 金融能力评测；
- gap：这些工作主要看金融知识、任务表现和答案正确性，较少评估金融任务中的显式交付约束。

## 7. Fig.1 Case 选择原则

用户明确指出：Fig.1 case 不能只是通用 JSON 约束失败，否则会让人觉得只需要提升一般 IF 能力，不需要 FinIF。

Fig.1 应展示：

- 强模型失败；
- 不是只违反一个 instruction，最好有多个约束失败；
- 至少包含金融特性的交付约束，例如数值精度、百分比表达、风险披露、投资语气、收益-风险配对、金融符号/单位规范等；
- 任务本身要有金融语境，例如财务分析、宏观数据、投资报告、风险总结等；
- 最好能体现“答案可能大体相关，但交付不合规”。

之前被否定的方向：只展示 JSON 输出失败的 case，因为 JSON 属于通用格式约束，不能证明金融 IF 的必要性。

候选方向：财政收入/支出、消费结构、公司财务指标或投资价值分析中，模型违反数值精度、百分比表达、风险披露、输出结构等多个约束的案例。

## 8. 已知项目事实

以下数字来自当前项目记录，可在写 contribution、dataset section、experiment section 时使用，但摘要中不一定要全部出现：

- FinIF-Test：100 cases。
- 指令约束：300 条。
- 硬约束 / 软约束：187 hard + 113 soft。
- 约束数量分布：1 条约束 15 个 case，2 条 20 个，3 条 30 个，4 条 20 个，5 条 15 个。
- 约束分类：5 大类 / 20 个子标签：Format、Number、Linguistic、Style、Content。
- FinIF-Train：2,134 prompts，转为 2,132 条 ShareGPT 训练样本。
- Teacher：GPT-5.4，经过 3 轮 repair，另有 15 条 manual repairs。
- 评测模型数量：10 个 LLM。
- Qwen3-8B SFT 提升：prompt-level 从 62.0% 到 77.0%，instruction-level 从 84.3% 到 91.3%。

部分最新结果：

- GPT-5.4：88.0 prompt / 96.0 instruction。
- GPT-5.2：87.0 / 95.7。
- GPT-5：77.0 / 92.0。
- Qwen3-8B-SFT：77.0 / 91.3。
- DS-V4-Pro-Think：77.0 / 90.7。
- DS-V4-Pro：76.0 / 90.0。
- DS-V4-Flash：75.0 / 90.0。
- DS-V4-Flash-Think：73.0 / 89.7。
- GPT-5.1：69.0 / 88.0。
- Qwen3-8B base：62.0 / 84.3。

## 9. 外部工作讨论记录

用户要求读过/了解过的相关方向：

- LongWriter / arXiv 2408.07055：可借鉴其“诊断瓶颈 -> 构造 benchmark/train data -> 评估和分析”的论文组织方式，但不要强行迁移。
- BankerToolBench：是金融 agent / 投行业务工作流 benchmark，重点是复杂工作流、专家 rubric、agent verifier。用户强调 FinIF 不是专门的金融文章或金融 agent benchmark，不能完全迁移。
- Anthropic `financial-services`：参考价值在于行业 agent 的组织方式，包括 Agent、Skill、Command、Connector、Human Review；但它主要是工作流参考方案，不是可直接使用的数据集。其数据连接偏海外金融数据源，对中国 A 股、基金、债券等需要迁移。

## 10. 后续接手建议

优先顺序建议：

1. 先根据固定故事线重写 abstract，每一句对应一个故事点，控制在 170-200 words。
2. 写 Introduction outline，并确定 Fig.1 case。
3. 整理 Related Work 的两节，每节只服务 gap，不写大综述。
4. 回到数据和实验，补清楚 task taxonomy、constraint taxonomy、synthetic pipeline、evaluation protocol。
5. 继续迭代 benchmark 难度，寻找能让强模型评分更低且具备金融特性的 case。

工作方式提醒：用户非常在意逻辑一致性。后续如果只是润色，不要调整叙事顺序；如果确实需要改逻辑，必须显式说明“这是逻辑改动”，并给出原因。
