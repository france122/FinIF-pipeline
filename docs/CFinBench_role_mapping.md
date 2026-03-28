# CFinBench 角色与法规语境映射

> 目的：不把 CFinBench 当作 query 来源，而把它当作**中国金融角色/岗位/法规语境库**，用于给开放式 query 模板填内容。
> 参考来源：`https://cfinbench.github.io/` 与 `CFinBench-Eval` README 中的 4 个一级类、43 个二级类。

---

## 一、总体判断

- `CFinBench` 的题型是：
  - single-choice
  - multiple-choice
  - judgment
- 因此它**不适合直接作为开放式 query 池来源**。
- 但它非常适合用来解决另一个问题：
  - **我们的开放式模板写成什么中国金融角色、什么岗位场景、什么制度语境才自然？**

一句话定位：

- **FIFE**：开放式任务模板库
- **CFinBench**：中国金融角色与语境词典

---

## 二、对 query 池最有价值的一级类

### 1. Financial Practice

这是最有价值的一层，因为它天然提供“谁在做事”。

可直接吸收的岗位包括：

- `Junior Auditor`
- `Intermediate Auditor`
- `Junior Statistician`
- `Intermediate Statistician`
- `Junior Economist`
- `Intermediate Economist`
- `Junior Banking Professional`
- `Intermediate Banking Professional`
- `Junior Accountant`
- `Intermediate Accountant`
- `Tax Consultant`
- `Asset Appraiser`
- `Securities Analyst`

这些岗位特别适合做 query 里的**角色设定**。

### 2. Financial Law

这是 query 中国化时非常重要的“制度语境层”。

可吸收的法规类包括：

- `Tax Law I`
- `Tax Law II`
- `Tax Inspection`
- `Commercial Law`
- `Securities Law`
- `Insurance Law`
- `Economic Law`
- `Banking Law`
- `Futures Law`
- `Financial Law`
- `Civil Law`

这些适合用来定义：

- 合规提醒
- 风险边界
- 披露义务
- 对客沟通的禁止性要求

### 3. Financial Qualification

这层不太适合直接做角色，但适合提供**能力语境**。

例如：

- `Tax Practitioner Qualification`
- `Fund Practitioner Qualification`
- `Insurance Practitioner Qualification`
- `Securities Practitioner Qualification`
- `Banking Practitioner Qualification`
- `Certified Public Accountant (CPA)`

它们可以作为：

- 从业人员培训材料
- 考试后真实工作场景延展
- 合规/知识问答的背景设定

---

## 三、与 4 个任务桶的映射

## 1. `finsuggestion`

### 最适合的角色

- `Securities Analyst`
- `Junior Economist`
- `Intermediate Economist`
- `Junior Banking Professional`
- `Intermediate Banking Professional`

### 典型 query 方向

- 投资建议
- 市场点评
- 资产配置建议
- 风险收益权衡 memo
- 面向客户或机构的建议性说明

### 最适合搭配的法规/制度语境

- `Securities Law`
- `Financial Law`
- `Banking Law`

### 示例改写方向

- 证券分析师 + 海外财报事实 + 写盘前点评
- 银行客户经理 + 客户风险偏好与产品信息 + 写配置建议
- 宏观研究员 + 央行政策材料 + 写政策影响分析

---

## 2. `findiag`

### 最适合的角色

- `Tax Consultant`
- `Junior Accountant`
- `Intermediate Accountant`
- `Junior Auditor`
- `Intermediate Auditor`
- `Asset Appraiser`

### 典型 query 方向

- 案例诊断
- 风险归因
- 合规判断
- 异常分析
- 对话后总结与建议

### 最适合搭配的法规/制度语境

- `Tax Law I/II`
- `Tax Inspection`
- `Economic Law`
- `Commercial Law`
- `Securities Law`

### 示例改写方向

- 税务顾问 + 企业情况材料 + 写风险诊断与后续处理建议
- 会计/审计岗位 + 异常凭证或流程材料 + 写问题归因 memo
- 合规人员 + 对话历史 + 写违规风险判断

---

## 3. `apiutil`

### 最适合的角色

- `Junior Statistician`
- `Intermediate Statistician`
- `Securities Analyst`
- `Junior Banking Professional`

### 典型 query 方向

- 如何抓取金融数据
- 如何调用行情 API
- 如何计算指标
- 如何写脚本/伪代码
- 如何做流程化数据处理

### 最适合搭配的制度语境

- 不强依赖具体法律，更依赖业务背景
- 可轻度搭配 `Securities Law` / `Banking Law` 做合规边界提醒

### 示例改写方向

- 证券分析师 + API 文档 + 写行情拉取流程
- 数据分析师 + 财务数据需求 + 写 Python 实现思路
- 银行科技/运营支持 + 接口说明 + 写自动化处理步骤

---

## 4. `finsales`

### 最适合的角色

- `Junior Banking Professional`
- `Intermediate Banking Professional`
- `Securities Analyst`（偏投教/对客说明）
- `Insurance Practitioner Qualification` 对应的保险销售/解释角色
- `Fund Practitioner Qualification` 对应的基金销售/投教角色

### 典型 query 方向

- 产品卖点说明
- 客户解释话术
- FAQ
- 路演/宣传文案
- 术语解释

### 最适合搭配的法规/制度语境

- `Securities Law`
- `Insurance Law`
- `Financial Law`
- `Banking Law`

### 示例改写方向

- 基金销售 + 产品事实包 + 写卖点说明
- 银行客户经理 + 客户疑问 + 写解释话术
- 保险顾问 + 产品条款 + 写 FAQ

---

## 四、推荐优先角色池

如果只选一批最适合 query 池 v2 的角色，我建议优先这 8 个：

1. `Securities Analyst`
2. `Tax Consultant`
3. `Junior Accountant`
4. `Intermediate Accountant`
5. `Junior Banking Professional`
6. `Intermediate Banking Professional`
7. `Junior Economist`
8. `Asset Appraiser`

原因：

- 都是现实金融工作流中经常需要写材料的人
- 容易与开放式模板结合
- 角色边界相对清晰
- 适合搭配“角色一致性约束”

---

## 五、与 FN-角色一致性约束的联动

你已采纳的新约束：

### `FN-角色一致性约束`

> 回答应符合指定金融角色的职责、语气和关注重点。

### rubric

- 0：明显不符合角色，甚至越权
- 1：略有角色痕迹，但大部分是泛化回答
- 2：基本符合角色，有一定角色特征
- 3：高度符合角色设定，职责边界、语气、重点都一致

### 因此 query 设计时应显式写出角色

推荐写法：

- “你是一名证券分析师……”
- “你是一名税务顾问……”
- “你是一名银行客户经理……”
- “你是一名合规审查人员……”
- “你是一名会计/审计从业人员……”

### 角色一致性可观察维度

1. **职责边界**
   - 是否越权做结论
   - 是否出现该角色通常不会说的话

2. **语气**
   - 分析师：专业、谨慎、数据导向
   - 客户经理：解释性、服务性、风险揭示
   - 合规人员：规则边界清晰、避免承诺
   - 税务顾问：强调适用条件、风险与口径

3. **关注重点**
   - 分析师：逻辑、数据、风险
   - 会计/审计：核对、证据、异常点
   - 银行从业人员：客户适配、收益风险、流程说明
   - 税务顾问：合法合规、条件、检查风险

---

## 六、使用方式建议

不要把 `CFinBench` 的题目直接改写成 query，而是把它当作一个“填空层”：

### 公式

`FIFE 模板 + CFinBench 角色 + 中国/跨境金融材料 + 角色一致性约束`

### 例子

1. **财报点评 brief**
   - 模板来源：FIFE 财报/market brief
   - 角色来源：`Securities Analyst`
   - 材料来源：美股或 A 股财报事实包
   - 可搭配约束：`FN-角色一致性约束`

2. **客户解释邮件**
   - 模板来源：FIFE client email
   - 角色来源：`Junior Banking Professional`
   - 材料来源：市场波动或理财产品材料
   - 可搭配约束：`FN-角色一致性约束`

3. **税务风险诊断 memo**
   - 模板来源：FIFE diagnosis / red flags / compliance note
   - 角色来源：`Tax Consultant`
   - 材料来源：企业情况与税务事实包
   - 可搭配约束：`FN-角色一致性约束`

---

## 七、落地结论

`CFinBench` 对 query 池重建最有价值的不是题目，而是：

- **职业角色**
- **岗位分层**
- **法规语境**
- **中国金融从业者的真实工作身份**

因此后续做 query 池 v2 时，推荐把 `CFinBench` 用作：

- 角色词典
- 法规背景词典
- 场景本土化约束层

而不是直接拿来抽题。

