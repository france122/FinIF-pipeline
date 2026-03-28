# FIFE 可迁移 Query 模板清单

> 目的：从 FIFE 的 88 条 query 中筛出适合扩充中文金融 IF query 池的任务模板。
> 使用原则：**借任务壳子，不直接照搬原文**。
> 参考文件：`/Users/minimax/Desktop/paper_research/FIFE_data_dashboard.md`

---

## 一、总体判断

- FIFE 的核心价值在于：提供了大量**开放式金融文档生成任务**的模板。
- FIFE 的局限在于：大量 query 场景**强绑定欧美监管、税制、结算基础设施**，不适合直接直译。
- 因此推荐的用法是：
  - 抽取任务模板
  - 替换为中国金融语境，或“中国机构处理全球金融信息”的真实工作流

---

## 二、与当前 4 个任务桶的对应关系

当前主任务桶：

- `finsuggestion`：建议、配置、风险收益权衡、客户沟通
- `findiag`：诊断、归因、复盘、基于材料的判断
- `apiutil`：工具/API/脚本/流程化操作说明
- `finsales`：营销话术、卖点提炼、产品解释、FAQ

FIFE 可迁移模板与之的关系：

| FIFE 模板形态 | 对应任务桶 | 备注 |
|---|---|---|
| 投资/市场 brief、建议 memo | `finsuggestion` | 最自然 |
| 风险/合规说明、案例诊断、归因总结 | `findiag` | 适合角色化与材料绑定 |
| 伪代码、公式说明、runbook、操作流程 | `apiutil` | 需替换为真实或半真实工具场景 |
| 客户邮件、FAQ、话术、产品卖点说明 | `finsales` | 适合搭配角色一致性约束 |

---

## 三、高可用模板（优先吸收）

这些模板的共同特点是：

- 输出空间大
- 任务目标清楚
- 不过度依赖欧美专属制度
- 容易换成中国金融机构或跨境研究场景

### A. 投资/市场简报类

1. **财报/市场点评 brief**
   - 代表：`#1` 权益分析、`#12` crypto market recap、`#16` ECB recap、`#28` EMBond quick paragraph
   - 可迁移为：
     - A 股/港股/美股财报点评
     - 宏观政策解读
     - 债券、外汇、商品市场点评
   - 适合任务桶：`finsuggestion` / `findiag`

2. **风险收益权衡 memo**
   - 代表：`#7` Treasury 二选一 memo
   - 可迁移为：
     - 现金管理方案比较
     - 理财/债基/货基配置比较
     - 外汇对冲与不对冲的取舍
   - 适合任务桶：`finsuggestion`

3. **管理层/路演 talking points**
   - 代表：`#6` CFO talking points、`#61` PE quarterly letter skeleton、`#88` IR roadshow
   - 可迁移为：
     - 业绩说明会要点
     - 产品路演提纲
     - 投资者沟通材料
   - 适合任务桶：`finsales` / `finsuggestion`

### B. 风险/诊断/合规类

4. **风险诊断与归因**
   - 代表：`#9` VaR math、`#35` model risk deficiencies、`#47` correlation takeaway、`#48` reverse-factoring red flags
   - 可迁移为：
     - 风险指标解释
     - 模型/产品缺陷诊断
     - 市场异动归因
   - 适合任务桶：`findiag`

5. **内部 advisory / compliance note**
   - 代表：`#4` MNPI advisory、`#32` AML procedures、`#72` 研究合规审查
   - 可迁移为：
     - 研究合规提醒
     - 内幕信息边界提醒
     - 金融产品销售合规提示
   - 适合任务桶：`findiag` / `finsales`

6. **案例分诊 / next actions**
   - 代表：`#58` AML case triage、`#81` credit limit changes summary
   - 可迁移为：
     - 客诉/风控案例处理
     - 交易异常初步判断
     - 授信/限额调整分析
   - 适合任务桶：`findiag`

### C. 话术/FAQ/产品解释类

7. **客户邮件 / explain-it-to-client**
   - 代表：`#3` FX move client email、`#27` retail liquidity note
   - 可迁移为：
     - 向客户解释市场波动
     - 向客户解释产品风险与收益
     - 向客户解释政策或估值变化
   - 适合任务桶：`finsales` / `finsuggestion`

8. **产品卖点说明 / factsheet skeleton**
   - 代表：`#14` REIT pitch、`#15` structured-product brief、`#77` fund factsheet
   - 可迁移为：
     - 公募基金卖点说明
     - REIT 产品介绍
     - 固收/结构化产品简要说明
   - 适合任务桶：`finsales`

9. **FAQ 模板**
   - 代表：`#44` ISO 20022 internal FAQ
   - 可迁移为：
     - 产品 FAQ
     - 政策变化 FAQ
     - 业务流程 FAQ
   - 适合任务桶：`finsales` / `apiutil`

### D. 工具/流程/脚本类

10. **伪代码 / workflow 说明**
   - 代表：`#11` quant pseudocode、`#22` CET1 bridge math、`#33` basis explainer + formula
   - 可迁移为：
     - 用 Python 抓取财务数据
     - 用 API 拉取行情并计算指标
     - 用伪代码说明数据处理流程
   - 适合任务桶：`apiutil`

11. **runbook / checklist / timeline**
   - 代表：`#20` timed checklist、`#53` settlement runbook、`#59` month-end runsheet、`#73/#75` cutover runbook
   - 可迁移为：
     - 数据拉取任务流程
     - 研报发布流程
     - 风险排查流程
     - 金融系统/运营流程清单
   - 适合任务桶：`apiutil`

12. **信息过滤 + 结构化输出**
   - 代表：`#76-88` 中的过滤、排序、计数、状态映射类
   - 可迁移为：
     - 从公告/台账/工单中筛出有效项
     - 根据条件汇总并输出表格或 checklist
   - 适合任务桶：`findiag` / `apiutil`

---

## 四、可改写模板（保留任务壳子，重写场景）

这些模板不是不能用，而是**必须重写角色或制度背景**。

1. **结算/清算/托管流程类**
   - 代表：`#5`、`#19`、`#31`、`#40`
   - 问题：Euroclear / Clearstream / DTC / CME / LCH 太欧美
   - 建议：保留“运营 checklist / 内部提醒 / 执行时间线”壳子，改成：
     - 银行间市场
     - 券商中后台
     - 公募/资管运营流程
     - 跨境业务支持流程

2. **税务合规规则过滤类**
   - 代表：`#25`、`#45`、`#85`
   - 问题：1099、TEY、carried-interest 等制度过美式
   - 建议：保留“规则过滤 + 备注 + 风险提示”壳子，换成：
     - 发票/税务核查
     - 适当性材料核验
     - 披露义务检查

3. **宏观与海外市场制度型场景**
   - 代表：`#16`、`#29`、`#33`
   - 问题：SOFR、RRP、ECB 等不一定适合境内通用 query
   - 建议：只有在明确设定为“中国机构关注海外市场”时才保留；否则改成：
     - 人民银行政策解读
     - 国债/利率债市场说明
     - 跨境宏观晨报

4. **支付/系统迁移类**
   - 代表：`#44`、`#63`、`#68`、`#73`、`#75`
   - 问题：SWIFT/CHAPS/PCI DSS 等语境不完全本土
   - 建议：可保留“FAQ / cutover runbook / onboarding checklist”结构，但要替换为国内支付、清算或企业金融 IT 流程

---

## 五、不建议直接使用的模板

这些模板与中国金融开放式 query 池的目标距离较远，建议只借 checker 或约束思路，不借 query。

1. **强监管编号绑定**
   - `#4` 中的 Rule 10b-5 精确引文
   - `#79` SEC filing pack
   - 原因：制度强绑定，直译后语境错位

2. **强税制绑定**
   - `#85` 1099-NEC candidates
   - 原因：规则本身就是美国税制

3. **强基础设施绑定**
   - `#5` Euroclear/Clearstream/DTC/CDS
   - `#19` CME margin alert
   - `#40` LCH margin formula
   - 原因：机构与 cut-off 机制不可直接照搬

4. **过度特定的欧美数据披露工作流**
   - `#11` 10-Q 抓取
   - `#44` SWIFT MT→MX / CHAPS
   - 原因：虽然任务壳子可借，但原 query 不值得直接改写

---

## 六、优先级建议

### 第一批优先吸收（最适合马上改写）

- `#1` 财报/观点 brief
- `#3` 客户解释邮件
- `#6` talking points
- `#7` 方案比较 memo
- `#9` 风险指标解释
- `#14` 产品推介
- `#27` 零售客户解释 note
- `#35` 风险缺陷总结
- `#41` 营销短文
- `#44` FAQ
- `#48` red flags callout
- `#54-58` 多步骤分析型模板
- `#61-63` 投资者信 / reserve / chargeback pack
- `#72-78` 研究合规 / cutover / 过滤 / rationalization

### 第二批条件吸收（需重写制度壳子）

- `#5`、`#19`、`#20`、`#31`、`#40`
- `#52`、`#73`、`#75`
- `#79`、`#83`、`#84`、`#85`、`#86`、`#87`

### 暂不作为 query 来源

- 纯欧美税法/清算/监管编号强绑定条目

---

## 七、落地建议

下一步生成新 query 时，不要写成“翻译 FIFE #n”，而要写成：

- 模板名
- 对应任务桶
- 可填充的角色
- 可填充的材料来源
- 是否适合搭配 `FN-角色一致性约束`

例如：

| 模板名 | 任务桶 | 角色示例 | 材料示例 | 角色一致性 |
|---|---|---|---|---|
| 财报点评 brief | `finsuggestion` | 证券分析师 | 财报新闻稿/关键财务数据 | 高 |
| 客户解释邮件 | `finsales` | 客户经理/投顾 | 市场波动事实包 | 高 |
| 风险诊断 memo | `findiag` | 风控专员 | 对话记录/异常指标 | 高 |
| API 操作说明 | `apiutil` | 数据分析师 | API 文档/任务需求 | 中 |

