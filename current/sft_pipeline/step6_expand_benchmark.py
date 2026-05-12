#!/usr/bin/env python3
"""
Step 6: 扩充 benchmark 从 54 → ~100 条
全部新增 case 使用真实外部数据（国家统计局 / 证监会 / 上市公司公告）

Context 严格分区：
  A组 = benchmark-only context（不进训练集）
  B组 = training-only context（synthetic，不进 benchmark）

输入:
  - benchmark_all.json + eval_config_all.json（现有 54 case / 256 约束）
  - raw_contexts_batch1/（13 个真实文档）
  - 内嵌的 stats.gov.cn 宏观数据

输出:
  - benchmark_all.json（扩充版，备份原文件）
  - eval_config_all.json（扩充版，备份原文件）
"""
import json, os, re, shutil, glob
from collections import Counter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPELINE_DIR = os.path.join(BASE_DIR, "sft_pipeline")
RAW_DIR = os.path.join(os.path.dirname(BASE_DIR), "raw_contexts_batch1")

BENCHMARK_PATH = os.path.join(BASE_DIR, "benchmark", "benchmark_all.json")
EVALCONFIG_PATH = os.path.join(BASE_DIR, "benchmark", "eval_config_all.json")

# ─── 宏观数据 contexts（来源: stats.gov.cn 2026年一季度）────────────────

CTX_GDP = """2026年一季度国民经济运行情况（来源：国家统计局 2026年4月16日发布）

一季度，国内生产总值334193亿元，按不变价格计算，同比增长5.0%，比上年四季度环比增长1.3%。分产业看，第一产业增加值11941亿元，同比增长3.8%；第二产业增加值116135亿元，增长4.9%；第三产业增加值206117亿元，增长5.2%。

一季度，规模以上工业增加值同比增长6.1%。分门类看，采矿业增长6.0%，制造业增长6.4%，电力、热力、燃气及水生产和供应业增长4.3%。装备制造业增加值增长8.9%，高技术制造业增加值增长12.5%。3月份，规模以上工业增加值同比增长5.7%。

一季度，社会消费品零售总额127695亿元，同比增长2.4%。按经营单位所在地分，城镇消费品零售额110574亿元，增长2.3%；乡村消费品零售额17121亿元，增长3.1%。按消费类型分，商品零售113072亿元，增长2.2%；餐饮收入14623亿元，增长4.2%。全国网上零售额49774亿元，增长8.0%。

一季度，全国固定资产投资（不含农户）102708亿元，同比增长1.7%。基础设施投资增长8.9%，制造业投资增长4.1%，房地产开发投资下降11.2%。高技术产业投资增长7.4%。

一季度，货物进出口总额118380亿元，同比增长15.0%。其中，出口68467亿元，增长11.9%；进口49913亿元，增长19.6%。进出口相抵，贸易顺差18554亿元。

一季度，全国居民消费价格（CPI）同比上涨0.9%。其中，3月份CPI同比上涨1.0%。核心CPI同比上涨1.2%。全国工业生产者出厂价格（PPI）同比下降0.6%。其中，3月份PPI同比上涨0.5%。

一季度，全国城镇调查失业率平均值为5.3%，与上年同期持平。3月份，全国城镇调查失业率为5.4%。"""

CTX_GDP_INDUSTRY = """2026年一季度国内生产总值（GDP）初步核算结果（来源：国家统计局 2026年4月17日发布）

2026年一季度国内生产总值为334193亿元，同比增长5.0%，环比增长1.3%。

分行业增加值数据如下：

| 行业 | 绝对额（亿元） | 同比增长（%） |
|------|----------------|--------------|
| 农林牧渔业 | 12851 | 4.0 |
| 工业 | 103388 | 6.1 |
| 其中：制造业 | 86960 | 6.3 |
| 建筑业 | 13632 | -3.8 |
| 批发和零售业 | 35071 | 4.1 |
| 交通运输、仓储和邮政业 | 14638 | 4.3 |
| 住宿和餐饮业 | 6055 | 4.3 |
| 金融业 | 27225 | 6.5 |
| 房地产业 | 20326 | -0.1 |
| 信息传输、软件和信息技术服务业 | 20444 | 10.6 |
| 租赁和商务服务业 | 16209 | 12.2 |
| 其他行业 | 64354 | 4.0 |

三次产业构成：第一产业增加值11941亿元（占比3.6%），第二产业增加值116135亿元（占比34.7%），第三产业增加值206117亿元（占比61.7%）。"""

CTX_INDUSTRIAL_PROFIT = """2026年1—3月份全国规模以上工业企业利润数据（来源：国家统计局 2026年4月27日发布）

一季度，全国规模以上工业企业实现利润总额16960.4亿元，同比增长15.5%。3月份利润同比增长15.8%。

营业收入33.19万亿元，同比增长5.0%；营业成本28.19万亿元，同比增长4.5%。营业收入利润率5.11%，同比提高0.46个百分点。

按经济类型分：
| 企业类型 | 利润总额（亿元） | 同比增长(%) |
|---------|-----------------|----------|
| 国有控股企业 | 6196.1 | 10.1 |
| 股份制企业 | 13054.6 | 20.9 |
| 外商及港澳台投资企业 | 3837.3 | 1.2 |
| 私营企业 | 4305.3 | 25.4 |

按行业分：
| 行业 | 利润总额（亿元） | 同比增长(%) |
|-----|-----------------|----------|
| 采矿业 | 2563.3 | 16.2 |
| 制造业 | 12384.3 | 19.1 |
| 电力、热力、燃气及水 | 2012.8 | -3.2 |

主要行业利润变化：
- 计算机、通信和其他电子设备制造业：增长124.5%
- 有色金属冶炼和压延加工业：增长116.7%
- 化学原料和化学制品制造业：增长54.5%
- 汽车制造业：下降17.7%
- 非金属矿物制品业：下降42.6%
- 黑色金属冶炼和压延加工业：由盈转亏

3月末资产负债情况：
- 资产总计190.50万亿元，同比增长5.3%
- 负债合计110.19万亿元，同比增长5.5%
- 所有者权益80.31万亿元，同比增长5.1%
- 资产负债率57.8%

运营效率：
- 每百元营业收入中的成本84.93元，同比减少0.40元
- 每百元营业收入中的费用8.50元，同比减少0.01元
- 应收账款27.03万亿元，同比增长6.7%
- 产成品存货6.78万亿元，同比增长5.2%"""

CTX_INCOME = """2026年一季度全国居民收入和消费支出情况（来源：国家统计局 2026年4月16日发布）

一、居民收入情况
一季度，全国居民人均可支配收入12782元，比上年同期名义增长4.9%，扣除价格因素，实际增长4.0%。

按收入来源分：工资性收入7319元，增长4.9%，占可支配收入的比重为57.3%；经营净收入2207元，增长6.6%，占比17.3%；财产净收入1031元，增长1.6%，占比8.1%；转移净收入2225元，增长5.1%，占比17.4%。

按常住地分，城镇居民人均可支配收入16549元，名义增长4.2%，实际增长3.2%；农村居民人均可支配收入7433元，名义增长6.1%，实际增长5.4%。城乡居民人均可支配收入比值为2.23。

全国居民人均可支配收入中位数10433元，增长5.0%，中位数是平均数的81.6%。

二、居民消费支出情况
一季度，全国居民人均消费支出7955元，比上年同期名义增长3.6%，扣除价格因素，实际增长2.6%。

按类别分：
| 消费类别 | 支出（元） | 增长(%) | 占比(%) |
|---------|-----------|---------|---------|
| 食品烟酒 | 2549 | 5.3 | 32.0 |
| 衣着 | 526 | 5.6 | 6.6 |
| 居住 | 1611 | 1.0 | 20.3 |
| 生活用品及服务 | 442 | 6.1 | 5.6 |
| 交通通信 | 1079 | 3.4 | 13.6 |
| 教育文化娱乐 | 843 | 2.5 | 10.6 |
| 医疗保健 | 645 | -0.5 | 8.1 |
| 其他用品及服务 | 260 | 10.2 | 3.3 |

按常住地分，城镇居民人均消费支出9635元，名义增长2.9%；农村居民人均消费支出5569元，名义增长4.4%。"""

CTX_REALESTATE = """2026年1—3月份全国房地产市场基本情况（来源：国家统计局 2026年4月16日发布）

一、房地产开发投资
全国房地产开发投资17720亿元，同比下降11.2%。其中，住宅投资13531亿元，下降11.0%。

房屋新开工面积10373万平方米，同比下降20.3%。其中住宅新开工面积7420万平方米，下降22.0%。
房屋竣工面积9789万平方米，同比下降25.0%。其中住宅竣工面积6983万平方米，下降26.5%。

二、商品房销售
新建商品房销售面积19525万平方米，同比下降10.4%（降幅比1—2月份收窄3.1个百分点）。其中住宅销售面积16008万平方米，下降13.1%。
新建商品房销售额17262亿元，同比下降16.7%（降幅比1—2月份收窄3.5个百分点）。其中住宅销售额14921亿元，下降18.5%。

3月末商品房待售面积78601万平方米，同比下降0.1%。其中住宅待售面积42771万平方米，增长1.4%。

三、资金到位情况
房地产开发企业到位资金20524亿元，同比下降17.3%。其中：
- 国内贷款3419亿元，下降23.7%
- 利用外资3亿元，增长127.6%
- 自筹资金7762亿元，下降5.3%
- 定金及预收款5858亿元，下降20.1%
- 个人按揭贷款2204亿元，下降34.6%

四、分地区数据
| 地区 | 投资额（亿元） | 投资增速(%) | 销售面积（万m²） | 销售额（亿元） | 销售额增速(%) |
|------|---------------|------------|----------------|--------------|-------------|
| 东部 | 10905 | -11.7 | 8611 | 10107 | -18.2 |
| 中部 | 3488 | -11.2 | 5259 | 3424 | -10.1 |
| 西部 | 3131 | -8.1 | 5072 | 3345 | -17.5 |
| 东北 | 196 | -31.6 | 583 | 385 | -25.1 |"""

CTX_INVESTMENT = """2026年1-3月份全国固定资产投资数据（来源：国家统计局 2026年4月16日发布）

一季度，全国固定资产投资（不含农户）102708亿元，同比增长1.7%。3月份环比增长0.52%。

分产业看：
| 产业 | 投资额（亿元） | 同比增速(%) |
|------|---------------|------------|
| 第一产业 | 2334 | 15.9 |
| 第二产业 | 36765 | 5.8 |
| 第三产业 | 63608 | -1.0 |

民间固定资产投资同比下降2.2%。国有控股投资同比增长7.1%。

工业投资增长5.8%，其中：采矿业增长15.0%，制造业增长4.1%，电力热力燃气及水增长9.0%。

基础设施投资增长8.9%，其中：航空运输业增长43.3%，水上运输业增长34.1%。

高技术产业投资增长7.4%。

分地区看：东部地区增长0.7%，中部地区增长1.9%，西部地区增长1.0%，东北地区下降10.0%。

按登记注册类型分：内资企业增长2.1%，港澳台投资企业下降5.0%，外商投资企业下降6.3%。"""

CTX_CPI_PPI = """2026年3月份CPI和PPI数据解读（来源：国家统计局城市司首席统计师董莉娟 2026年4月10日发布）

一、CPI数据
3月份，全国居民消费价格（CPI）同比上涨1.0%，核心CPI同比上涨1.1%。CPI环比下降0.7%。

同比分项：
- 食品价格上涨0.3%
- 非食品价格上涨1.2%
- 工业消费品价格上涨2.2%
- 服务价格上涨0.8%

食品细项（同比）：
- 鲜菜上涨7.8%
- 鲜果上涨4.0%
- 牛肉上涨5.2%
- 猪肉下降11.5%
- 鸡蛋下降3.3%

非食品亮点（同比）：
- 黄金饰品上涨65.8%
- 汽油上涨3.8%
- 家用器具上涨2.4%
- 服装上涨1.7%

一季度CPI同比上涨0.9%。

二、PPI数据
3月份，全国工业生产者出厂价格（PPI）同比上涨0.5%，为连续下降41个月后首次上涨。PPI环比上涨1.0%，已连续6个月环比上涨。

主要行业（同比）：
- 有色金属矿采选业上涨36.4%
- 有色金属冶炼和压延加工业上涨22.4%
- 石油和天然气开采业上涨5.2%
- 光纤制造上涨76.1%

一季度PPI同比下降0.6%。"""


# ─── 辅助函数 ─────────────────────────────────────────────────────

def read_pdf(path):
    from pypdf import PdfReader
    reader = PdfReader(path)
    pages = []
    for p in reader.pages:
        t = p.extract_text()
        if t:
            pages.append(t)
    raw = "\n".join(pages)
    lines = raw.splitlines()
    cleaned = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if re.match(r'^https?://', line):
            continue
        if re.match(r'^\d+\s*/\s*\d+$', line):
            continue
        if re.match(r'^第\s*\d+\s*页', line):
            continue
        if len(line) < 3 and not re.search(r'[一-鿿]', line):
            continue
        cleaned.append(line)
    text = "\n".join(cleaned)
    return text[:6000] if len(text) > 6000 else text


def read_md(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return text[:6000] if len(text) > 6000 else text


def load_batch1():
    """读取 raw_contexts_batch1 中的真实文档"""
    docs = {}
    if not os.path.isdir(RAW_DIR):
        print(f"WARNING: {RAW_DIR} not found, skipping batch1 docs")
        return docs
    for fname in sorted(os.listdir(RAW_DIR)):
        fpath = os.path.join(RAW_DIR, fname)
        if fname.endswith('.pdf'):
            docs[fname] = read_pdf(fpath)
        elif fname.endswith('.md'):
            docs[fname] = read_md(fpath)
    return docs


def make_prompt(context, task):
    """组装 prompt = context + 任务指令"""
    return f"{context}\n\n{task}"


# ─── 定义新增 benchmark cases ─────────────────────────────────────

def build_new_cases(batch1_docs):
    """返回 (cases_list, constraints_dict)"""
    cases = []
    constraints = {}

    def add(case_id, context, task, constraint_list):
        cases.append({
            "case_id": case_id,
            "prompt": make_prompt(context, task),
            "context": context,
        })
        for i, c in enumerate(constraint_list, 1):
            key = f"{case_id}#C{i}"
            constraints[key] = c

    # ════════════════════════════════════════════════════════════
    #  T1.1 数据提取与基础计算 (现有 12, 目标 +10 = 22)
    # ════════════════════════════════════════════════════════════

    add("T1.1-013", CTX_GDP,
        """请基于以上国民经济数据，完成以下分析：

1. 提取一季度GDP总值及三大产业增加值
2. 计算第三产业增加值占GDP的比重（保留一位小数）
3. 计算贸易顺差金额（出口额 - 进口额）
4. 提取CPI和PPI的一季度同比数据

输出要求：使用Markdown表格汇总所有提取的数据，计算过程需展示。""",
        [
            {"type": "hard", "checker": "check_value_exact",
             "description": "GDP和三大产业数据与原文一致",
             "params": {"expected_values": {"GDP": "334193", "第一产业": "11941", "第二产业": "116135", "第三产业": "206117"}}},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算第三产业占比",
             "params": {"results": [{"label": "第三产业占比", "expected": 61.7, "tolerance": 0.3}]}},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算贸易顺差",
             "params": {"results": [{"label": "贸易顺差", "expected": 18554, "tolerance": 10}]}},
            {"type": "soft", "description": "CPI和PPI数据提取完整",
             "rubric": "输出应包含一季度CPI同比0.9%、PPI同比-0.6%、3月CPI同比1.0%、3月PPI同比0.5%等数据"},
            {"type": "soft", "description": "使用Markdown表格汇总",
             "rubric": "输出应使用Markdown表格格式汇总所有关键数据，而非仅用文字叙述"},
        ])

    add("T1.1-014", CTX_GDP_INDUSTRY,
        """请基于以上GDP分行业数据，完成以下分析：

1. 提取增速最高和最低的两个行业及其增加值
2. 计算工业增加值占GDP的百分比（保留一位小数）
3. 计算金融业增加值与房地产业增加值的差额
4. 哪些行业出现负增长？列出行业名称和增速

输出要求：使用Markdown格式，需展示计算过程。""",
        [
            {"type": "hard", "checker": "check_value_exact",
             "description": "正确识别增速最高和最低行业",
             "params": {"expected_values": {"增速最高": "租赁和商务服务业", "最高增速": "12.2"}}},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算工业占GDP比重",
             "params": {"results": [{"label": "工业占比", "expected": 30.9, "tolerance": 0.3}]}},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算金融业与房地产业差额",
             "params": {"results": [{"label": "差额", "expected": 6899, "tolerance": 10}]}},
            {"type": "soft", "description": "完整列出负增长行业",
             "rubric": "应列出建筑业（-3.8%）和房地产业（-0.1%）两个负增长行业"},
        ])

    add("T1.1-015", CTX_CPI_PPI,
        """请基于以上CPI和PPI数据，完成以下分析：

1. 提取3月份CPI同比和环比数据
2. 提取食品分项中涨幅最大和降幅最大的细项
3. PPI已连续下降多少个月后首次上涨？连续环比上涨多少个月？
4. 计算CPI食品价格与非食品价格的同比涨幅差（非食品 - 食品）

输出要求：使用Markdown格式，计算过程需展示。""",
        [
            {"type": "hard", "checker": "check_value_exact",
             "description": "CPI数据与原文一致",
             "params": {"expected_values": {"CPI同比": "1.0", "CPI环比": "-0.7", "核心CPI": "1.1"}}},
            {"type": "hard", "checker": "check_value_exact",
             "description": "PPI转正月数正确",
             "params": {"expected_values": {"连续下降月数": "41", "连续环比上涨月数": "6"}}},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算食品与非食品涨幅差",
             "params": {"results": [{"label": "涨幅差", "expected": 0.9, "tolerance": 0.1}]}},
            {"type": "soft", "description": "正确识别食品涨跌幅极值",
             "rubric": "涨幅最大应为鲜菜(7.8%)，降幅最大应为猪肉(-11.5%)"},
        ])

    add("T1.1-016", CTX_INDUSTRIAL_PROFIT,
        """请基于以上工业企业利润数据，完成以下分析：

1. 提取四种经济类型企业的利润总额和增速
2. 计算私营企业利润占全部利润总额的比重
3. 计算营业成本占营业收入的比例
4. 资产负债率是多少？资产总计与负债合计的差额是多少？

输出要求：使用Markdown格式，需展示计算过程。""",
        [
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算私营企业利润占比",
             "params": {"results": [{"label": "私营企业占比", "expected": 25.4, "tolerance": 0.5}]}},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算成本收入比",
             "params": {"results": [{"label": "成本收入比", "expected": 84.93, "tolerance": 0.1}]}},
            {"type": "hard", "checker": "check_value_exact",
             "description": "资产负债率与原文一致",
             "params": {"expected_values": {"资产负债率": "57.8"}}},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算资产-负债差额（所有者权益）",
             "params": {"results": [{"label": "所有者权益", "expected": 80.31, "tolerance": 0.1}]}},
        ])

    add("T1.1-017", CTX_INCOME,
        """请基于以上居民收入和消费数据，完成以下分析：

1. 提取全国居民人均可支配收入及四项收入来源的金额和占比
2. 计算城镇与农村居民人均可支配收入的绝对差额
3. 验证四项收入来源之和是否等于人均可支配收入总额，展示验算过程
4. 居民人均可支配收入中位数与平均数的比值是多少？

输出要求：使用Markdown格式，需展示计算过程。""",
        [
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算城乡收入差额",
             "params": {"results": [{"label": "城乡差额", "expected": 9116, "tolerance": 10}]}},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确验算四项收入来源之和",
             "params": {"results": [{"label": "收入合计", "expected": 12782, "tolerance": 10}]}},
            {"type": "hard", "checker": "check_value_exact",
             "description": "中位数/平均数比值与原文一致",
             "params": {"expected_values": {"中位数占平均数比例": "81.6"}}},
            {"type": "soft", "description": "完整提取四项收入数据",
             "rubric": "应列出工资性收入7319元(57.3%)、经营净收入2207元(17.3%)、财产净收入1031元(8.1%)、转移净收入2225元(17.4%)"},
        ])

    # 风险提示公告
    ctx_risk1 = batch1_docs.get("股票交易风险提示公告.pdf", "")
    if ctx_risk1:
        add("T1.1-018", ctx_risk1,
            """请基于以上股票交易风险提示公告，完成以下分析：

1. 提取公司证券代码、证券简称和公告编号
2. 提取累计涨幅和连续涨停天数
3. 提取宝光联悦的营业收入及占合并营业收入比例
4. 计算宝光联悦净利润占合并净利润的比例是否与公告一致

输出要求：使用Markdown格式，计算过程需展示。""",
            [
                {"type": "hard", "checker": "check_value_exact",
                 "description": "证券信息正确",
                 "params": {"expected_values": {"证券代码": "600379", "证券简称": "宝光股份"}}},
                {"type": "hard", "checker": "check_value_exact",
                 "description": "涨幅和涨停数据正确",
                 "params": {"expected_values": {"累计涨幅": "46.51", "连续涨停": "4"}}},
                {"type": "hard", "checker": "check_value_exact",
                 "description": "子公司收入占比正确",
                 "params": {"expected_values": {"宝光联悦营业收入": "4404.45", "收入占比": "3.49"}}},
                {"type": "soft", "description": "分析子公司占比判断炒作风险",
                 "rubric": "应指出子公司业务收入占比极小(3.49%)，净利润占比也很低(6.23%)，市场存在过度炒作风险"},
            ])

    ctx_risk2 = batch1_docs.get("股票交易风险提示公告2.pdf", "")
    if ctx_risk2:
        add("T1.1-019", ctx_risk2,
            """请基于以上股票交易风险提示公告，完成以下分析：

1. 提取公司的基本信息（证券代码、简称、所属交易所）
2. 提取所有涉及的数值数据（涨幅、价格、财务指标等），按类别分组
3. 如果公告中提到了异常波动相关数据，计算波动幅度
4. 总结公告提示的核心风险点

输出要求：使用Markdown格式，数据须逐项列出。""",
            [
                {"type": "hard", "checker": "check_value_exact",
                 "description": "正确提取公司基本信息",
                 "params": {"expected_values": {}}},  # 将根据实际文本填充
                {"type": "soft", "description": "完整提取所有数值数据",
                 "rubric": "输出应系统性地提取公告中出现的所有数值数据，按类别（行情数据、财务数据、风险指标）分组"},
                {"type": "soft", "description": "准确总结核心风险点",
                 "rubric": "应总结出股价异常波动、基本面与股价偏离、投机炒作等核心风险"},
            ])

    add("T1.1-020", CTX_INVESTMENT,
        """请基于以上固定资产投资数据，完成以下分析：

1. 提取三大产业的投资额和增速
2. 计算第二产业和第三产业投资额之和占总投资的比重
3. 民间投资与国有控股投资的增速差是多少个百分点？
4. 哪个地区投资增速最低？与最高地区相差多少个百分点？

输出要求：使用Markdown格式，需展示计算过程。""",
        [
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算二三产业占比",
             "params": {"results": [{"label": "二三产业占比", "expected": 97.7, "tolerance": 0.3}]}},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算民间与国有增速差",
             "params": {"results": [{"label": "增速差", "expected": 9.3, "tolerance": 0.2}]}},
            {"type": "hard", "checker": "check_value_exact",
             "description": "正确识别投资增速最低地区",
             "params": {"expected_values": {"投资增速最低地区": "东北"}}},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算地区增速极差",
             "params": {"results": [{"label": "地区增速极差", "expected": 11.9, "tolerance": 0.2}]}},
        ])

    add("T1.1-021", CTX_REALESTATE,
        """请基于以上房地产市场数据，完成以下分析：

1. 提取房地产开发投资总额及住宅投资占比
2. 计算新建商品房平均售价（销售额/销售面积），单位为元/平方米
3. 在资金来源中，哪项降幅最大？降幅是多少？
4. 东部地区销售额占全国的比重是多少？

输出要求：使用Markdown格式，需展示计算过程。""",
        [
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算住宅投资占比",
             "params": {"results": [{"label": "住宅投资占比", "expected": 76.4, "tolerance": 0.5}]}},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算平均售价",
             "params": {"results": [{"label": "平均售价", "expected": 8842, "tolerance": 50}]}},
            {"type": "hard", "checker": "check_value_exact",
             "description": "正确识别降幅最大的资金来源",
             "params": {"expected_values": {"降幅最大项": "个人按揭贷款", "降幅": "34.6"}}},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算东部销售额占比",
             "params": {"results": [{"label": "东部占比", "expected": 58.6, "tolerance": 0.5}]}},
        ])

    # ════════════════════════════════════════════════════════════
    #  T1.2 财务指标分析 (现有 7, 目标 +7 = 14)
    # ════════════════════════════════════════════════════════════

    add("T1.2-008", CTX_INDUSTRIAL_PROFIT,
        """请基于以上工业企业利润数据，完成以下财务指标分析：

1. 计算采矿业利润占工业利润总额的比重
2. 每百元营业收入中成本同比减少0.40元，计算成本下降对利润率的贡献
3. 应收账款增速(6.7%)与营业收入增速(5.0%)的差异说明了什么？
4. 比较国有控股企业与私营企业的利润增速差异，分析原因

输出要求：使用Markdown格式，需展示计算过程和分析逻辑。""",
        [
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算采矿业利润占比",
             "params": {"results": [{"label": "采矿业占比", "expected": 15.1, "tolerance": 0.3}]}},
            {"type": "soft", "description": "分析成本下降对利润率的贡献",
             "rubric": "应说明成本从85.33元降至84.93元，推动利润率从4.65%提升至5.11%，成本每降低1元约对应利润率提升1个百分点"},
            {"type": "soft", "description": "分析应收账款与收入增速差异",
             "rubric": "应指出应收账款增速高于收入增速1.7个百分点，说明回款压力增大或信用销售比例提高"},
            {"type": "soft", "description": "对比分析国有与私营企业利润差异",
             "rubric": "应指出私营企业利润增速(25.4%)显著高于国有控股(10.1%)，并结合行业结构分析"},
        ])

    ctx_annual = batch1_docs.get("2025*ST恒久年度报告.pdf", "")
    if ctx_annual:
        add("T1.2-009", ctx_annual,
            """请基于以上*ST恒久年度报告摘要，完成以下财务分析：

1. 提取公司的未弥补亏损金额
2. 公司为何被出具无法表示意见的审计报告？
3. 提取报告中所有出现的财务数据（收入、利润、资产等）
4. 基于现有数据，分析公司面临的主要财务风险

输出要求：使用Markdown格式，数据须准确标注来源段落。""",
            [
                {"type": "hard", "checker": "check_value_exact",
                 "description": "正确提取未弥补亏损",
                 "params": {"expected_values": {"未弥补亏损": "62374794.23"}}},
                {"type": "soft", "description": "正确解释审计意见类型的含义",
                 "rubric": "应解释无法表示意见是最严重的审计意见类型，通常意味着审计范围严重受限或持续经营存在重大不确定性"},
                {"type": "soft", "description": "全面分析财务风险",
                 "rubric": "应涵盖持续经营风险、累计亏损、利润分配无法进行、退市风险等要点"},
                {"type": "soft", "description": "数据标注来源段落",
                 "rubric": "每个数据点应标注其来源（如'年报摘要第一部分'或对应段落），而非仅列出数字"},
            ])

    ctx_jianchi = batch1_docs.get("减持公告.pdf", "")
    if ctx_jianchi:
        add("T1.2-010", ctx_jianchi,
            """请基于以上减持公告，完成以下分析：

1. 提取减持主体名称和被减持公司信息
2. 计划减持的最大股份数量是多少？（集中竞价 + 大宗交易合计）
3. 减持比例上限分别是多少？
4. 减持期间的时间窗口是多长？

输出要求：使用Markdown格式，需展示计算过程。""",
            [
                {"type": "hard", "checker": "check_value_exact",
                 "description": "正确提取减持主体和标的",
                 "params": {"expected_values": {"减持主体": "永辉超市", "被减持公司": "红旗连锁", "证券代码": "002697"}}},
                {"type": "hard", "checker": "check_computation_result",
                 "description": "正确计算合计最大减持量",
                 "params": {"results": [{"label": "合计最大减持量", "expected": 40800000, "tolerance": 100}]}},
                {"type": "hard", "checker": "check_value_exact",
                 "description": "减持比例正确",
                 "params": {"expected_values": {"集中竞价比例上限": "1%", "大宗交易比例上限": "2%"}}},
                {"type": "soft", "description": "正确说明减持时间窗口",
                 "rubric": "应说明减持期间为预披露公告发布之日起15个交易日后的3个月内"},
            ])

    ctx_inquiry3 = batch1_docs.get("问询函3.pdf", "")
    if ctx_inquiry3:
        add("T1.2-011", ctx_inquiry3,
            """请基于以上问询函内容，完成以下分析：

1. 提取问询函涉及的所有财务数据
2. 问询函关注的核心问题是什么？
3. 如果问询函中提到了财务指标变动，计算变动幅度
4. 总结监管方的主要关注点

输出要求：使用Markdown格式，按问题分类整理。""",
            [
                {"type": "soft", "description": "完整提取所有财务数据",
                 "rubric": "应系统性提取问询函中涉及的所有金额、比例、增速等数值数据"},
                {"type": "soft", "description": "准确识别核心问题",
                 "rubric": "应识别出监管方关注的核心问题类别（如关联交易、业绩真实性、资金占用等）"},
                {"type": "soft", "description": "按问题分类整理",
                 "rubric": "输出应按监管关注的不同问题类别分节组织，而非简单罗列"},
            ])

    add("T1.2-012", CTX_REALESTATE,
        """请基于以上房地产市场数据，完成以下财务指标分析：

1. 计算住宅投资占总投资的比重，以及住宅销售面积占总销售面积的比重
2. 用销售额/销售面积计算全国、东部、中部、西部的平均售价，并排序
3. 计算到位资金与投资额的比值（资金保障倍数）
4. 自筹资金占到位资金的比重，与上年同期相比资金结构有何变化趋势？

输出要求：使用Markdown表格展示计算结果，需展示过程。""",
        [
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算住宅投资占比",
             "params": {"results": [{"label": "住宅投资占比", "expected": 76.4, "tolerance": 0.5}]}},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算全国平均售价",
             "params": {"results": [{"label": "全国均价", "expected": 8842, "tolerance": 50}]}},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算资金保障倍数",
             "params": {"results": [{"label": "资金保障倍数", "expected": 1.16, "tolerance": 0.02}]}},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算自筹资金占比",
             "params": {"results": [{"label": "自筹资金占比", "expected": 37.8, "tolerance": 0.5}]}},
        ])

    add("T1.2-013", CTX_GDP,
        """请基于以上国民经济数据，完成以下分析：

1. 计算一季度净出口（出口-进口）占GDP的比重
2. 计算社会消费品零售总额占GDP的比重
3. 固定资产投资占GDP的比重是多少？
4. 对比三驾马车（消费、投资、净出口）对GDP的贡献大小，排序

输出要求：使用Markdown格式，需展示计算过程，比重保留一位小数。""",
        [
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算净出口占GDP比重",
             "params": {"results": [{"label": "净出口占GDP", "expected": 5.6, "tolerance": 0.3}]}},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算消费占GDP比重",
             "params": {"results": [{"label": "消费占GDP", "expected": 38.2, "tolerance": 0.3}]}},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算投资占GDP比重",
             "params": {"results": [{"label": "投资占GDP", "expected": 30.7, "tolerance": 0.3}]}},
            {"type": "soft", "description": "正确排序三驾马车贡献",
             "rubric": "按占GDP比重排序应为消费>投资>净出口"},
        ])

    add("T1.2-014", CTX_INCOME,
        """请基于以上居民收入和消费数据，完成以下分析：

1. 计算居民消费率（人均消费支出/人均可支配收入）
2. 计算恩格尔系数（食品烟酒支出/消费总支出）
3. 城镇居民实际收入增速与农村居民实际收入增速差是多少？
4. 名义增长率与实际增长率之差反映了什么？计算隐含的物价水平

输出要求：使用Markdown格式，需展示计算过程，百分比保留一位小数。""",
        [
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算消费率",
             "params": {"results": [{"label": "消费率", "expected": 62.2, "tolerance": 0.5}]}},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算恩格尔系数",
             "params": {"results": [{"label": "恩格尔系数", "expected": 32.0, "tolerance": 0.3}]}},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算城乡实际增速差",
             "params": {"results": [{"label": "实际增速差", "expected": 2.2, "tolerance": 0.2}]}},
            {"type": "soft", "description": "正确分析名义与实际增长率之差",
             "rubric": "应指出名义增长4.9%与实际增长4.0%之差约0.9个百分点，反映了CPI通胀率约0.9%，与一季度CPI同比0.9%基本一致"},
        ])

    # ════════════════════════════════════════════════════════════
    #  T1.3 结构化数据展示 (现有 8, 目标 +6 = 14)
    # ════════════════════════════════════════════════════════════

    add("T1.3-009", CTX_GDP,
        """请将以上一季度国民经济数据整理为结构化的JSON格式报告。

要求：
1. 顶层key为: gdp, industry, consumption, investment, trade, price, employment
2. 每个key下包含核心指标的键值对
3. 数值字段统一使用浮点数，不含单位
4. 增速字段以百分比数值表示
5. 在每个大类下新增 "highlight" 字段，用一句话总结该类数据的核心特点

输出要求：输出有效的JSON格式，不要包含注释。""",
        [
            {"type": "hard", "checker": "check_json_format",
             "description": "输出为合法JSON格式",
             "params": {"required_keys": ["gdp", "industry", "consumption", "investment", "trade", "price", "employment"]}},
            {"type": "soft", "description": "数值字段正确且完整",
             "rubric": "JSON中的数值应与原文一致，如gdp.total=334193, gdp.growth=5.0等"},
            {"type": "soft", "description": "每个大类有highlight摘要",
             "rubric": "每个大类下应有highlight字段，用一句话准确总结该领域的核心特点"},
            {"type": "soft", "description": "增速字段使用百分比数值",
             "rubric": "增速字段如growth应使用5.0而非\"5.0%\"，保持数据可计算性"},
        ])

    add("T1.3-010", CTX_INDUSTRIAL_PROFIT,
        """请将以上工业企业利润数据整理为排名表格。

要求：
1. 制作"主要行业利润增速排名表"，包含列：排名、行业名称、利润增速(%)
2. 增速从高到低排列
3. 由盈转亏或由亏转盈的行业单独标注
4. 在表格下方给出前3名和后3名的简要分析

输出要求：使用Markdown表格格式。""",
        [
            {"type": "soft", "description": "表格包含所有行业且排序正确",
             "rubric": "应包含计算机通信(124.5%)、有色金属(116.7%)、化学原料(54.5%)等增长行业和汽车(-17.7%)、非金属矿物(-42.6%)、黑色金属(由盈转亏)等下降行业，按增速降序排列"},
            {"type": "soft", "description": "正确标注盈亏转换行业",
             "rubric": "应标注黑色金属冶炼(由盈转亏)和石油煤炭加工(由亏转盈)"},
            {"type": "soft", "description": "包含前3名和后3名分析",
             "rubric": "表格下方应分析增速最高的3个行业和最低的3个行业的特点"},
            {"type": "soft", "description": "使用规范的Markdown表格",
             "rubric": "使用标准Markdown表格语法，包含表头分隔行（|---|---|---|），对齐整洁"},
        ])

    add("T1.3-011", CTX_INCOME,
        """请将以上居民消费支出数据整理为Markdown表格。

要求：
1. 制作"一季度居民消费支出结构表"，包含列：类别、支出金额（元）、同比增长(%)、占比(%)
2. 按占比从高到低排列
3. 增加合计行
4. 用↑↓箭头标注增速是正是负

输出要求：使用Markdown表格格式，合计行数据需正确。""",
        [
            {"type": "hard", "checker": "check_computation_result",
             "description": "合计行金额正确",
             "params": {"results": [{"label": "消费合计", "expected": 7955, "tolerance": 5}]}},
            {"type": "soft", "description": "排序正确（按占比降序）",
             "rubric": "排序应为：食品烟酒(32.0%)>居住(20.3%)>交通通信(13.6%)>教育文化(10.6%)>医疗保健(8.1%)>衣着(6.6%)>生活用品(5.6%)>其他(3.3%)"},
            {"type": "soft", "description": "箭头标注正确",
             "rubric": "医疗保健(-0.5%)应标↓，其余7项均标↑"},
            {"type": "soft", "description": "Markdown表格格式规范",
             "rubric": "使用标准Markdown表格，包含表头、分隔行、数据行和合计行"},
        ])

    add("T1.3-012", CTX_REALESTATE,
        """请将以上房地产数据整理为分地区对比表。

要求：
1. 制作"一季度分地区房地产关键指标对比表"
2. 列：地区、投资额（亿元）、投资增速(%)、销售面积（万m²）、销售额（亿元）、销售额增速(%)、均价（元/m²）
3. 均价列需自行计算（销售额/销售面积 × 10000）
4. 增加全国汇总行

输出要求：使用Markdown表格格式。""",
        [
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算东部地区均价",
             "params": {"results": [{"label": "东部均价", "expected": 11737, "tolerance": 100}]}},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算全国均价",
             "params": {"results": [{"label": "全国均价", "expected": 8842, "tolerance": 50}]}},
            {"type": "soft", "description": "表格完整包含四个地区和全国行",
             "rubric": "应包含东部、中部、西部、东北四个地区以及全国汇总行"},
            {"type": "soft", "description": "使用规范Markdown表格",
             "rubric": "使用标准Markdown表格语法，数据对齐，列名清晰"},
        ])

    add("T1.3-013", CTX_GDP_INDUSTRY,
        """请将以上GDP分行业数据整理为两个表格。

表格1: "正增长行业排名（按增速降序）"
列：排名、行业、增加值（亿元）、同比增长(%)

表格2: "负增长行业"
列：行业、增加值（亿元）、同比增长(%)

要求：正增长和负增长严格分开，增速为0视为正增长。

输出要求：使用Markdown表格格式。""",
        [
            {"type": "soft", "description": "正增长行业排序正确",
             "rubric": "正增长行业按增速降序：租赁和商务服务业(12.2%)>信息技术(10.6%)>金融业(6.5%)>制造业(6.3%)>工业(6.1%)>..."},
            {"type": "soft", "description": "负增长行业识别完整",
             "rubric": "负增长行业为建筑业(-3.8%)和房地产业(-0.1%)"},
            {"type": "soft", "description": "数据与原文一致",
             "rubric": "所有增加值和增速数据应与原文表格完全一致"},
            {"type": "soft", "description": "使用两个独立Markdown表格",
             "rubric": "应输出两个标题明确的独立表格，而非合并为一个"},
        ])

    add("T1.3-014", CTX_INVESTMENT,
        """请将以上固定资产投资数据整理为多维度对比报告。

要求：
1. 表格1: 按产业分（第一/二/三产业），含投资额和增速
2. 表格2: 按地区分（东部/中部/西部/东北），含增速
3. 表格3: 按企业性质分（内资/港澳台/外商），含增速
4. 每个表格下方用一句话总结核心发现

输出要求：使用Markdown表格格式，共三个表格。""",
        [
            {"type": "soft", "description": "三个表格数据完整正确",
             "rubric": "三个表格应覆盖产业、地区、企业性质三个维度，数据与原文一致"},
            {"type": "soft", "description": "每个表格有核心发现总结",
             "rubric": "如：产业维度应指出第一产业增速最快(15.9%)，第三产业负增长(-1.0%)；地区维度应指出东北降幅最大(-10.0%)"},
            {"type": "soft", "description": "使用规范Markdown格式",
             "rubric": "每个表格有清晰标题，使用标准Markdown表格语法"},
        ])

    # ════════════════════════════════════════════════════════════
    #  T2.1 综合分析 (现有 3, 目标 +5 = 8)
    # ════════════════════════════════════════════════════════════

    add("T2.1-004", CTX_GDP,
        """请基于以上一季度国民经济数据，撰写一份综合分析报告（800-1200字）。

分析要求：
1. 总体判断：经济运行的整体态势
2. 亮点分析：哪些领域表现突出？
3. 短板分析：哪些领域存在压力？
4. 结构特征：消费/投资/出口三驾马车的各自表现
5. 政策建议：基于数据给出1-2条政策建议

输出要求：分节撰写，引用具体数据支撑分析。""",
        [
            {"type": "hard", "checker": "check_word_range",
             "description": "字数在800-1200字范围内",
             "params": {"min_words": 800, "max_words": 1200}},
            {"type": "soft", "description": "包含五个分析维度",
             "rubric": "报告应包含总体判断、亮点、短板、结构特征、政策建议五个部分"},
            {"type": "soft", "description": "引用具体数据支撑",
             "rubric": "每个分析点应引用具体数据，如GDP增长5.0%、高技术制造业增长12.5%、房地产投资下降11.2%等"},
            {"type": "soft", "description": "分析逻辑合理",
             "rubric": "亮点应包含出口(15.0%)、高技术制造(12.5%)等；短板应包含房地产(-11.2%)、消费偏弱(2.4%)等"},
        ])

    add("T2.1-005", CTX_REALESTATE,
        """请基于以上房地产市场数据，撰写一份综合分析报告（600-1000字）。

分析要求：
1. 投资端：开发投资、新开工、竣工的变化趋势
2. 销售端：销售面积、销售额、均价分析
3. 资金端：到位资金结构分析
4. 区域分化：不同地区的市场差异
5. 趋势判断：市场是否出现边际改善信号？

输出要求：分节撰写，引用具体数据。""",
        [
            {"type": "hard", "checker": "check_word_range",
             "description": "字数在600-1000字范围内",
             "params": {"min_words": 600, "max_words": 1000}},
            {"type": "soft", "description": "五个维度分析完整",
             "rubric": "应覆盖投资、销售、资金、区域、趋势五个方面"},
            {"type": "soft", "description": "识别边际改善信号",
             "rubric": "应指出销售降幅收窄（面积降幅收窄3.1个百分点，额降幅收窄3.5个百分点）作为边际改善迹象"},
            {"type": "soft", "description": "区域分析有差异对比",
             "rubric": "应对比东部(高均价低增速)vs中部vs西部vs东北(降幅最大)的差异"},
        ])

    ctx_inquiry1 = batch1_docs.get("问询函.pdf", "")
    if ctx_inquiry1:
        add("T2.1-006", ctx_inquiry1,
            """请基于以上交易所问询函，完成以下综合分析：

1. 梳理问询函提出的所有问题清单
2. 按重要性排序，分析每个问题的监管意图
3. 评估这些问题反映出公司可能存在的哪些风险
4. 如果你是公司管理层，建议如何回复每个问题

输出要求：分节撰写，按问题逐一分析。""",
            [
                {"type": "soft", "description": "完整梳理问询函问题",
                 "rubric": "应列出问询函中提出的所有明确问题"},
                {"type": "soft", "description": "分析监管意图",
                 "rubric": "应从信息披露合规、投资者保护、风险提示等角度分析每个问题的监管意图"},
                {"type": "soft", "description": "评估公司风险",
                 "rubric": "应基于问询内容推断公司可能存在的经营、财务或合规风险"},
                {"type": "soft", "description": "回复建议合理",
                 "rubric": "建议应具体、可操作，包含需要披露的具体信息类型"},
            ])

    ctx_inquiry2 = batch1_docs.get("问询函2.pdf", "")
    if ctx_inquiry2:
        add("T2.1-007", ctx_inquiry2,
            """请基于以上问询函内容，完成以下分析：

1. 总结问询函的核心关注领域
2. 分析被问询公司的信息披露是否存在不充分之处
3. 评估该问询可能对公司股价和市场信心的影响
4. 给出公司需要补充披露的信息清单

输出要求：使用Markdown格式，分点论述。""",
            [
                {"type": "soft", "description": "准确识别核心关注领域",
                 "rubric": "应从问询函内容中准确提炼出监管关注的核心领域"},
                {"type": "soft", "description": "分析信息披露不充分之处",
                 "rubric": "应具体指出原公告中哪些信息需要补充或澄清"},
                {"type": "soft", "description": "市场影响分析合理",
                 "rubric": "应分析问询函对投资者信心和股价可能产生的短期和中期影响"},
            ])

    add("T2.1-008", CTX_INDUSTRIAL_PROFIT,
        """请基于以上工业企业利润数据，进行综合分析（500-800字）。

分析要求：
1. 利润结构：采矿 vs 制造 vs 电力的格局变化
2. 所有制差异：国有、股份制、外商、私营的利润增速对比
3. 行业分化：高增长vs负增长行业的特征分析
4. 效率指标：从资产负债率、成本利润率角度评估

输出要求：分节撰写，引用具体数据。""",
        [
            {"type": "hard", "checker": "check_word_range",
             "description": "字数在500-800字范围内",
             "params": {"min_words": 500, "max_words": 800}},
            {"type": "soft", "description": "四个维度分析完整",
             "rubric": "应覆盖利润结构、所有制差异、行业分化、效率指标四个方面"},
            {"type": "soft", "description": "行业分化分析有深度",
             "rubric": "应指出电子信息(+124.5%)和有色金属(+116.7%)的高增长与汽车(-17.7%)、非金属矿(-42.6%)的衰退形成鲜明对比"},
        ])

    # ════════════════════════════════════════════════════════════
    #  T2.2 多维度评估 (现有 3, 目标 +3 = 6)
    # ════════════════════════════════════════════════════════════

    add("T2.2-004", CTX_INCOME,
        """请基于以上居民收入消费数据，从以下维度进行多角度评估：

1. 收入质量：工资性收入占比是否合理？财产性收入偏低说明什么？
2. 消费倾向：消费率是否偏低？恩格尔系数处于什么水平？
3. 城乡差距：城乡收入比2.23意味着什么？差距在缩小还是扩大？
4. 收入分配：中位数/平均数比值81.6%反映了怎样的分配状况？

输出要求：使用Markdown格式，每个维度给出明确的评估结论。""",
        [
            {"type": "soft", "description": "收入质量评估合理",
             "rubric": "应指出工资性收入占比57.3%偏高（过度依赖劳动报酬），财产净收入占比8.1%偏低（资本收入不足）"},
            {"type": "soft", "description": "消费倾向分析有依据",
             "rubric": "应计算消费率约62%，恩格尔系数32%处于富裕标准（<30%为最富裕），说明基本需求已较好满足"},
            {"type": "soft", "description": "城乡差距分析客观",
             "rubric": "应指出城乡收入比2.23仍较高，但农村增速(6.1%)高于城镇(4.2%)说明差距在缩小"},
            {"type": "soft", "description": "分配状况解读正确",
             "rubric": "中位数/平均数比值81.6%<100%说明高收入群体拉高了平均数，存在一定程度的收入不平等"},
        ])

    add("T2.2-005", CTX_GDP_INDUSTRY,
        """请基于以上GDP分行业数据，对中国经济产业结构进行多维度评估：

1. 结构转型：第三产业占比61.7%处于什么发展阶段？
2. 新旧动能：信息技术(10.6%)、租赁商务(12.2%)等新经济行业的贡献如何？
3. 风险行业：建筑业(-3.8%)和房地产(-0.1%)的负增长意味着什么？
4. 制造业地位：制造业增加值86960亿元在GDP中的地位评估

输出要求：每个维度给出评估结论和数据支撑。""",
        [
            {"type": "soft", "description": "结构转型评估合理",
             "rubric": "应指出第三产业占比61.7%已超过60%，处于服务经济阶段，符合发达经济体转型趋势"},
            {"type": "soft", "description": "新旧动能分析有深度",
             "rubric": "应对比新经济行业(信息技术10.6%、租赁商务12.2%)与传统行业的增速差异"},
            {"type": "soft", "description": "风险行业分析到位",
             "rubric": "应分析建筑业和房地产负增长对经济的拖累效应，以及对就业和地方财政的影响"},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算制造业占GDP比重",
             "params": {"results": [{"label": "制造业占GDP", "expected": 26.0, "tolerance": 0.3}]}},
        ])

    if ctx_annual:
        add("T2.2-006", ctx_annual,
            """请基于以上*ST恒久年度报告摘要，对公司经营状况进行多维度评估：

1. 持续经营能力：从审计意见、累计亏损角度评估
2. 财务健康度：从利润分配、资产质量角度评估
3. 退市风险：公司面临哪些退市触发条件？
4. 综合评级：给出投资价值评估（强烈不推荐/不推荐/中性/推荐）

输出要求：使用Markdown格式，每个维度给出明确评估结论。""",
            [
                {"type": "soft", "description": "持续经营评估准确",
                 "rubric": "应指出无法表示意见的审计报告和未弥补亏损62,374,794.23元是严重的持续经营警示"},
                {"type": "soft", "description": "退市风险分析全面",
                 "rubric": "应分析*ST标识的含义、连续亏损可能触发的退市风险警示等"},
                {"type": "soft", "description": "综合评级有理有据",
                 "rubric": "基于审计意见和亏损状况，评级应为强烈不推荐或不推荐"},
            ])

    # ════════════════════════════════════════════════════════════
    #  T2.3 趋势与对比分析 (现有 3, 目标 +3 = 6)
    # ════════════════════════════════════════════════════════════

    add("T2.3-004", CTX_INDUSTRIAL_PROFIT,
        """请基于以上工业企业利润数据，进行趋势与对比分析：

1. 对比四种经济类型企业（国有/股份制/外商/私营）的利润增速，分析差异原因
2. 对比三大门类（采矿/制造/电力）的利润结构变化
3. 增长最快（计算机通信124.5%）与下降最快（非金属矿物-42.6%）的行业对比分析
4. 营业收入增速(5.0%) vs 利润增速(15.5%)的剪刀差说明了什么？

输出要求：使用Markdown格式，配合数据对比分析。""",
        [
            {"type": "soft", "description": "四种经济类型对比分析合理",
             "rubric": "应对比国有(10.1%)、股份制(20.9%)、外商(1.2%)、私营(25.4%)的增速差异，分析结构性原因"},
            {"type": "soft", "description": "三大门类结构分析到位",
             "rubric": "应计算三大门类利润占比：采矿(15.1%)、制造(73.0%)、电力(11.9%)"},
            {"type": "soft", "description": "极值行业对比有深度",
             "rubric": "应分析电子信息和有色金属高增长的驱动因素（如AI需求、金属价格上涨）与非金属矿物下降的原因（房地产下行拖累）"},
            {"type": "soft", "description": "剪刀差分析正确",
             "rubric": "应指出利润增速远高于收入增速说明成本控制改善和利润率提升"},
        ])

    add("T2.3-005", CTX_REALESTATE,
        """请基于以上房地产数据，进行分地区趋势对比分析：

1. 四个地区的投资增速对比，哪个地区降幅最大？为什么？
2. 用销售额/销售面积计算四个地区的均价，对比价格差异
3. 东北地区各项指标全面大幅下降，分析可能的结构性原因
4. 销售降幅收窄（面积收窄3.1pct，额收窄3.5pct）是否意味着市场回暖？

输出要求：使用Markdown格式，配合计算和数据对比。""",
        [
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算东部均价",
             "params": {"results": [{"label": "东部均价", "expected": 11737, "tolerance": 100}]}},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算西部均价",
             "params": {"results": [{"label": "西部均价", "expected": 6596, "tolerance": 100}]}},
            {"type": "soft", "description": "东北下降原因分析合理",
             "rubric": "应分析东北人口流出、经济增长乏力、气候因素等结构性原因"},
            {"type": "soft", "description": "降幅收窄判断审慎",
             "rubric": "应分析降幅收窄是积极信号，但仍为两位数下降，不宜过度乐观"},
        ])

    add("T2.3-006", CTX_CPI_PPI,
        """请基于以上CPI和PPI数据，进行物价趋势分析：

1. CPI食品vs非食品的走势对比
2. PPI连续下降41个月后首次转正的经济含义
3. CPI同比1.0%与核心CPI同比1.1%的关系说明什么？
4. 黄金饰品价格上涨65.8%，这一异常涨幅的原因和对CPI的影响

输出要求：使用Markdown格式，结合宏观经济背景分析。""",
        [
            {"type": "soft", "description": "食品vs非食品分析正确",
             "rubric": "应指出食品价格仅涨0.3%（猪肉-11.5%拖累），非食品涨1.2%高于食品，说明结构性特征"},
            {"type": "soft", "description": "PPI转正分析有深度",
             "rubric": "应分析PPI结束41个月通缩的意义：工业品需求回暖、企业盈利改善、有色金属价格大涨驱动"},
            {"type": "soft", "description": "CPI与核心CPI关系解读正确",
             "rubric": "核心CPI(1.1%)高于总CPI(1.0%)说明剔除食品能源后的通胀水平略高，内需有一定支撑"},
            {"type": "soft", "description": "黄金价格分析合理",
             "rubric": "应分析国际金价上涨、避险需求、央行购金等原因，以及其对CPI的权重影响有限"},
        ])

    # ════════════════════════════════════════════════════════════
    #  T2.4 风险评估 (现有 2, 目标 +6 = 8)
    # ════════════════════════════════════════════════════════════

    add("T2.4-003", CTX_REALESTATE,
        """请基于以上房地产市场数据，进行系统性风险评估。

评估维度：
1. 投资下行风险：开发投资-11.2%、新开工-20.3%、竣工-25.0%的趋势
2. 销售端风险：销售面积和销售额双降对开发商现金流的影响
3. 资金链风险：到位资金-17.3%，尤其个人按揭贷款-34.6%的含义
4. 区域分化风险：东北投资-31.6%是否存在系统性崩溃风险
5. 总体风险评级：高/中/低，并说明依据

输出要求：使用Markdown格式，每个维度给出风险等级和依据。""",
        [
            {"type": "soft", "description": "五个风险维度分析完整",
             "rubric": "应覆盖投资、销售、资金、区域、总体五个风险维度"},
            {"type": "soft", "description": "资金链风险分析到位",
             "rubric": "应重点分析个人按揭贷款-34.6%对开发商回款的冲击，以及自筹资金占比上升的被动性"},
            {"type": "soft", "description": "区域风险差异化评估",
             "rubric": "东北应评为高风险（投资-31.6%、销售-25.1%），东部中等风险，中西部中等偏低"},
            {"type": "soft", "description": "总体评级有逻辑支撑",
             "rubric": "总体风险评级应有明确依据，结合降幅收窄的积极信号和持续大幅下降的负面因素"},
        ])

    add("T2.4-004", CTX_INVESTMENT,
        """请基于以上固定资产投资数据，评估投资结构的潜在风险。

评估维度：
1. 民间投资萎缩风险：民间投资-2.2% vs 国有控股+7.1%的分化
2. 区域失衡风险：东北-10.0%是否会加剧区域经济差距
3. 外资撤退风险：外商投资-6.3%、港澳台-5.0%的趋势
4. 结构性风险：第三产业投资-1.0%对就业和消费的影响
5. 给出各维度风险等级和总体评估

输出要求：使用Markdown格式，配合数据分析。""",
        [
            {"type": "soft", "description": "民间投资萎缩分析合理",
             "rubric": "应指出民间投资占总投资比重大，-2.2%反映市场信心不足，国有增长7.1%可能有政府稳增长托底"},
            {"type": "soft", "description": "外资趋势分析到位",
             "rubric": "应分析外商(-6.3%)和港澳台(-5.0%)投资下降是否与关税政策、地缘政治有关"},
            {"type": "soft", "description": "第三产业影响评估合理",
             "rubric": "应指出第三产业投资负增长对服务业就业和消费的潜在影响"},
            {"type": "soft", "description": "风险等级明确",
             "rubric": "每个维度应给出明确的高/中/低风险评级"},
        ])

    add("T2.4-005", CTX_INDUSTRIAL_PROFIT,
        """请基于以上工业企业利润数据，评估工业领域的结构性风险。

评估维度：
1. 行业集中风险：利润增长是否过度依赖少数行业（电子、有色）？
2. 传统行业衰退风险：非金属矿-42.6%、黑色金属由盈转亏的影响
3. 应收账款风险：应收账款增速(6.7%)快于收入增速(5.0%)的风险
4. 外商企业风险：外商企业利润仅增1.2%的含义

输出要求：使用Markdown格式，每个维度给出风险评估和建议。""",
        [
            {"type": "soft", "description": "行业集中风险分析合理",
             "rubric": "应分析计算机通信(124.5%)和有色金属(116.7%)对整体利润增长的拉动是否可持续"},
            {"type": "soft", "description": "传统行业衰退分析到位",
             "rubric": "应关联非金属矿物与房地产下行，黑色金属与钢铁产能过剩的逻辑链"},
            {"type": "soft", "description": "应收账款风险评估正确",
             "rubric": "应指出应收账款/收入增速剪刀差扩大说明回款困难，可能引发坏账风险"},
        ])

    # 从年报做风险评估
    if ctx_annual:
        add("T2.4-006", ctx_annual,
            """请基于以上*ST恒久年度报告摘要，对公司进行持续经营风险评估。

评估维度：
1. 审计风险：无法表示意见的审计报告意味着什么？
2. 亏损风险：未弥补亏损对公司运营的影响
3. 退市风险：*ST标识下公司面临的退市情景
4. 治理风险：从利润分配方案看公司治理状况
5. 综合风险评级和投资者建议

输出要求：使用Markdown格式，给出明确的风险等级。""",
            [
                {"type": "soft", "description": "审计风险分析正确",
                 "rubric": "应解释无法表示意见是最严重的审计意见，说明审计师无法获取充分审计证据或存在重大不确定性"},
                {"type": "soft", "description": "退市风险评估全面",
                 "rubric": "应分析*ST→退市风险警示→暂停上市→终止上市的路径"},
                {"type": "soft", "description": "综合评级为高风险",
                 "rubric": "综合评级应为高风险或极高风险，建议投资者规避"},
            ])

    # 从风险提示公告做风险评估
    if ctx_risk1:
        add("T2.4-007", ctx_risk1,
            """请基于以上股票交易风险提示公告，评估投资者面临的风险。

评估维度：
1. 炒作风险：连续涨停后的追高风险评估
2. 基本面风险：子公司业务(收入占比3.49%)能否支撑当前股价
3. 信息不对称风险：市场热点与公司实际经营的偏差
4. 给出明确的投资风险等级和建议

输出要求：使用Markdown格式，引用公告中的具体数据。""",
            [
                {"type": "soft", "description": "炒作风险评估准确",
                 "rubric": "应指出连续4个交易日涨停、累计涨幅46.51%存在严重的投机炒作特征"},
                {"type": "soft", "description": "基本面偏离分析到位",
                 "rubric": "应用子公司收入占比3.49%、净利润占比6.23%说明热点业务对公司基本面贡献极小"},
                {"type": "soft", "description": "风险等级明确",
                 "rubric": "风险等级应为高风险，建议谨慎，不宜追高"},
            ])

    add("T2.4-008", CTX_GDP,
        """请基于以上一季度宏观经济数据，评估中国经济面临的主要风险。

评估维度：
1. 内需不足风险：消费增长2.4%是否偏低？
2. 房地产风险：房地产开发投资-11.2%、销售-16.7%的拖累效应
3. 就业风险：城镇调查失业率5.3%是否处于可控范围？
4. 外部风险：进出口高增长(15.0%)的可持续性
5. 总体风险评估

输出要求：使用Markdown格式，每个维度给出风险等级和依据。""",
        [
            {"type": "soft", "description": "内需风险分析合理",
             "rubric": "应指出消费增长2.4%低于GDP增速5.0%，说明消费动力不足，消费降级趋势需关注"},
            {"type": "soft", "description": "房地产拖累分析到位",
             "rubric": "应量化房地产投资下降对固投和GDP的拖累程度"},
            {"type": "soft", "description": "外部风险分析审慎",
             "rubric": "应分析出口高增长是否受关税预期影响的抢出口效应，可持续性存疑"},
            {"type": "soft", "description": "风险等级明确",
             "rubric": "每个维度应给出明确风险等级"},
        ])

    # ════════════════════════════════════════════════════════════
    #  T2.5 格式密集型 (现有 4, 目标 +3 = 7)
    # ════════════════════════════════════════════════════════════

    ctx_punishment_hc = batch1_docs.get("中国证监会行政处罚决定书（惠程科技）_中国证券监督管理委员会.pdf", "")
    if ctx_punishment_hc:
        add("T2.5-005", ctx_punishment_hc,
            """请将以上证监会行政处罚决定书改写为结构化信息卡片格式。

格式要求：
1. 【案件基本信息】：文号、当事人、住所、处罚日期
2. 【违法事实】：按时间线整理，每条事实用"[时间] 事件描述"格式
3. 【处罚依据】：引用的法律法规条文
4. 【处罚决定】：对每位当事人的具体处罚措施
5. 【关键数据表】：涉及的所有金额、比例等数值数据

输出要求：使用Markdown格式，严格按照上述5个板块组织。""",
            [
                {"type": "soft", "description": "包含全部5个结构化板块",
                 "rubric": "输出应包含案件基本信息、违法事实、处罚依据、处罚决定、关键数据表五个部分"},
                {"type": "soft", "description": "违法事实按时间线整理",
                 "rubric": "违法事实应按时间先后排列，使用统一的时间标注格式"},
                {"type": "soft", "description": "处罚决定对每位当事人分别列出",
                 "rubric": "应分别列出惠程科技、寇汉、汪超涌、赵红艳等当事人的处罚措施"},
                {"type": "soft", "description": "关键数据表完整",
                 "rubric": "应提取文书中涉及的所有金额、比例等数值数据，整理为表格"},
            ])

    add("T2.5-006", CTX_GDP,
        """请将以上一季度国民经济数据改写为一份投资简报。

格式要求：
1. 【核心摘要】：3个要点，每点不超过30字
2. 【数据速览】：5个最关键的指标，用"指标名 | 数值 | 趋势"三列表格
3. 【投资机会】：基于数据提出2个投资方向
4. 【风险提示】：基于数据列出2个需警惕的风险
5. 【下期关注】：列出3个需要持续跟踪的指标

输出要求：严格按照上述格式，简洁精炼。""",
        [
            {"type": "soft", "description": "核心摘要简洁有力",
             "rubric": "3个要点应捕捉最关键信息，每点不超过30字"},
            {"type": "soft", "description": "数据速览选取合理",
             "rubric": "5个指标应选择最有投资参考价值的数据（如GDP增速、出口增速、CPI、高技术制造增速等）"},
            {"type": "soft", "description": "投资方向有数据支撑",
             "rubric": "投资方向应基于数据推导（如高技术制造12.5%增长→科技板块；出口15%→出口相关行业）"},
            {"type": "soft", "description": "格式严格符合要求",
             "rubric": "应严格按照5个板块组织，使用指定的格式标记"},
        ])

    add("T2.5-007", CTX_INCOME,
        """请将以上居民收入消费数据改写为问答（Q&A）格式的分析报告。

格式要求：
1. 设计6个有价值的问题（Q1-Q6）
2. 每个问题的回答（A）不超过100字
3. 每个回答必须引用至少一个具体数据
4. 问题应覆盖收入、消费、城乡、结构等不同维度

输出要求：严格使用 Q: / A: 格式，6组问答。""",
        [
            {"type": "soft", "description": "包含6组问答",
             "rubric": "应恰好包含6组Q&A，覆盖不同维度"},
            {"type": "soft", "description": "每个回答引用具体数据",
             "rubric": "每个A中至少引用一个来自原文的具体数值"},
            {"type": "soft", "description": "回答简洁不超过100字",
             "rubric": "每个A应控制在100字以内"},
            {"type": "soft", "description": "问题覆盖多个维度",
             "rubric": "6个问题应分别覆盖总体收入、收入来源、城乡差距、消费结构、消费倾向、分配状况等维度"},
        ])

    # ════════════════════════════════════════════════════════════
    #  T3.1 复杂推理 (现有 4, 目标 +4 = 8)
    # ════════════════════════════════════════════════════════════

    ctx_punishment_tf = batch1_docs.get("中国证监会行政处罚决定书（涂尔帆）_中国证券监督管理委员会.pdf", "")
    if ctx_punishment_tf:
        add("T3.1-005", ctx_punishment_tf,
            """请基于以上证监会行政处罚决定书，进行法律推理分析：

1. 梳理当事人的违法行为链：动机 → 行为 → 后果
2. 证监会认定违法的法律依据是什么？
3. 处罚的合理性分析：处罚力度是否与违法严重程度匹配？
4. 如果当事人申请行政复议，可能的抗辩理由有哪些？

输出要求：使用Markdown格式，推理过程需逻辑清晰。""",
            [
                {"type": "soft", "description": "违法行为链梳理清晰",
                 "rubric": "应按动机→行为→后果的逻辑链梳理，每个环节有文书原文支撑"},
                {"type": "soft", "description": "法律依据引用正确",
                 "rubric": "应准确引用文书中提及的《证券法》相关条款"},
                {"type": "soft", "description": "处罚合理性分析有理有据",
                 "rubric": "应从违法金额、影响范围、主观恶意等角度分析处罚是否适当"},
                {"type": "soft", "description": "抗辩理由分析合理",
                 "rubric": "应考虑程序合法性、主观过错程度、从轻情节等可能的抗辩角度"},
            ])

    ctx_market_ban_zy = batch1_docs.get("中国证监会市场禁入决定书（张志勇）_中国证券监督管理委员会.pdf", "")
    if ctx_market_ban_zy:
        add("T3.1-006", ctx_market_ban_zy,
            """请基于以上证监会市场禁入决定书，进行复杂推理分析：

1. 市场禁入与行政处罚的区别是什么？为何本案适用市场禁入？
2. 当事人的哪些行为构成了"情节严重"的认定？
3. 禁入期限的确定依据是什么？
4. 该决定对市场秩序的警示作用分析

输出要求：使用Markdown格式，逻辑推理需严密。""",
            [
                {"type": "soft", "description": "市场禁入vs行政处罚区分正确",
                 "rubric": "应解释市场禁入是更严厉的监管措施，禁止当事人在一定期限内从事证券市场相关工作"},
                {"type": "soft", "description": "情节严重认定分析到位",
                 "rubric": "应结合文书内容分析具体构成\"情节严重\"的行为"},
                {"type": "soft", "description": "禁入期限分析合理",
                 "rubric": "应分析禁入期限与违法行为严重程度的对应关系"},
            ])

    ctx_punishment_lhz = batch1_docs.get("中国证监会行政处罚决定书（刘惠忠）_中国证券监督管理委员会.pdf", "")
    if ctx_punishment_lhz:
        add("T3.1-007", ctx_punishment_lhz,
            """请基于以上行政处罚决定书，分析以下问题：

1. 当事人的违法行为属于哪种类型（信息披露违法/内幕交易/操纵市场/其他）？
2. 从当事人的身份和职务推理其违法动机
3. 处罚金额的计算逻辑是什么？是否有"没一罚N"的倍数关系？
4. 如果类似行为在2024年新《证券法》下处理，处罚会更重还是更轻？

输出要求：使用Markdown格式，推理过程清晰。""",
            [
                {"type": "soft", "description": "违法类型识别正确",
                 "rubric": "应准确识别当事人违法行为的类型"},
                {"type": "soft", "description": "动机推理合理",
                 "rubric": "应从当事人的身份、职务和行为模式推理违法动机"},
                {"type": "soft", "description": "处罚逻辑分析到位",
                 "rubric": "应分析罚款金额与违法所得或违法金额的倍数关系"},
            ])

    ctx_market_ban_wgs = batch1_docs.get("中国证监会市场禁入决定书（吴光胜）_中国证券监督管理委员会.pdf", "")
    if ctx_market_ban_wgs:
        add("T3.1-008", ctx_market_ban_wgs,
            """请基于以上市场禁入决定书，进行以下推理分析：

1. 梳理当事人的完整违法事实时间线
2. 分析当事人在公司治理中的角色和责任
3. 从市场禁入的角度，推理监管层对此类行为的严惩态度
4. 如果该案涉及刑事责任，可能触发哪些罪名？

输出要求：使用Markdown格式，分点推理。""",
            [
                {"type": "soft", "description": "时间线梳理完整",
                 "rubric": "应按时间先后梳理所有违法事实，标注关键时间节点"},
                {"type": "soft", "description": "角色责任分析到位",
                 "rubric": "应分析当事人作为公司高管的决策责任和监督责任"},
                {"type": "soft", "description": "刑事责任推理合理",
                 "rubric": "应结合违法事实分析可能涉及的刑事罪名（如虚假陈述罪、操纵证券市场罪等）"},
            ])

    # ════════════════════════════════════════════════════════════
    #  T3.2 综合报告 (现有 4, 目标 +4 = 8)
    # ════════════════════════════════════════════════════════════

    if ctx_punishment_hc:
        add("T3.2-005", ctx_punishment_hc,
            """请基于以上惠程科技行政处罚决定书，撰写一份综合分析报告（800-1200字）。

报告结构：
1. 案件概述（100字以内）
2. 违法事实详析
3. 法律适用分析
4. 处罚结果及合理性评估
5. 案件启示与投资者保护建议

输出要求：使用Markdown格式，分节撰写，引用文书原文。""",
            [
                {"type": "hard", "checker": "check_word_range",
                 "description": "字数在800-1200字范围内",
                 "params": {"min_words": 800, "max_words": 1200}},
                {"type": "soft", "description": "五个部分结构完整",
                 "rubric": "应包含案件概述、违法事实、法律适用、处罚评估、启示建议五个完整部分"},
                {"type": "soft", "description": "引用文书原文",
                 "rubric": "分析中应引用行政处罚决定书中的原始表述，用引号标注"},
                {"type": "soft", "description": "投资者保护建议切实可行",
                 "rubric": "建议应针对类似案件给出具体的投资者识别和防范方法"},
            ])

    ctx_fraud = batch1_docs.get("最高人民法院发布造假典型案例.md", "")
    if ctx_fraud:
        add("T3.2-006", ctx_fraud,
            """请基于以上最高人民法院造假典型案例，撰写一份法律分析报告（600-1000字）。

报告结构：
1. 案件背景概述
2. 造假手法分析
3. 法院判决要点
4. 与证监会行政处罚的协同关系
5. 对资本市场诚信建设的启示

输出要求：使用Markdown格式，分节撰写。""",
            [
                {"type": "hard", "checker": "check_word_range",
                 "description": "字数在600-1000字范围内",
                 "params": {"min_words": 600, "max_words": 1000}},
                {"type": "soft", "description": "五个部分结构完整",
                 "rubric": "应包含背景、手法、判决、协同、启示五个部分"},
                {"type": "soft", "description": "造假手法分析具体",
                 "rubric": "应具体分析案例中的造假手段，如虚构交易、虚增收入等"},
                {"type": "soft", "description": "行政-刑事协同分析到位",
                 "rubric": "应分析行政处罚与刑事追责的衔接机制"},
            ])

    if ctx_market_ban_wgs:
        add("T3.2-007", ctx_market_ban_wgs,
            """请基于以上市场禁入决定书，撰写一份监管执法案例分析报告。

报告结构：
1. 案件摘要
2. 违法行为分类与严重程度评估
3. 监管执法的力度与效果评价
4. 同类案件的历史比较（推测可能的同类案件处理趋势）
5. 对上市公司治理的启示

输出要求：使用Markdown格式，分节撰写。""",
            [
                {"type": "soft", "description": "报告结构完整",
                 "rubric": "应包含摘要、分类评估、执法评价、历史比较、治理启示五个部分"},
                {"type": "soft", "description": "严重程度评估有标准",
                 "rubric": "应从涉案金额、影响范围、持续时间、主观恶意等维度评估严重程度"},
                {"type": "soft", "description": "治理启示有建设性",
                 "rubric": "应给出上市公司如何完善内控、防范类似违法行为的具体建议"},
            ])

    add("T3.2-008", CTX_GDP + "\n\n" + CTX_REALESTATE,
        """请基于以上一季度GDP和房地产市场数据，撰写一份宏观经济运行综合报告（1000-1500字）。

报告结构：
1. 总体经济研判
2. 核心驱动力分析（出口、投资、消费）
3. 房地产对经济的拖累效应量化分析
4. 物价走势与货币政策空间
5. 下一季度展望与政策建议

输出要求：使用Markdown格式，分节撰写，需引用具体数据支撑每个论点。""",
        [
            {"type": "hard", "checker": "check_word_range",
             "description": "字数在1000-1500字范围内",
             "params": {"min_words": 1000, "max_words": 1500}},
            {"type": "soft", "description": "五个部分结构完整",
             "rubric": "应包含总体研判、驱动力、房地产拖累、物价政策、展望建议五个部分"},
            {"type": "soft", "description": "房地产拖累量化分析",
             "rubric": "应尝试量化房地产投资-11.2%对固投1.7%增长的拖累贡献"},
            {"type": "soft", "description": "每个论点有数据支撑",
             "rubric": "每个分析论点应至少引用一个具体数据指标"},
        ])

    # ════════════════════════════════════════════════════════════
    #  T3.3 高阶推导 (现有 4, 目标 +2 = 6)
    # ════════════════════════════════════════════════════════════

    add("T3.3-005", CTX_INCOME,
        """请基于以上居民收入消费数据，进行以下高阶推导：

1. 已知名义增长4.9%、实际增长4.0%，推导隐含的价格指数（CPI）近似值
2. 城乡收入比为2.23，农村增速6.1%、城镇增速4.2%，按此趋势推算多少年后城乡收入比降到2.0以下？
3. 当前消费率（消费/收入）约为62%，如果消费率提升1个百分点到63%，将额外释放多少消费（按14亿人口计算）
4. 从恩格尔系数32%推断居民生活水平处于什么阶段？

输出要求：使用Markdown格式，展示详细推导过程和公式。""",
        [
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确推导隐含CPI",
             "params": {"results": [{"label": "隐含CPI", "expected": 0.9, "tolerance": 0.2}]}},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确推算城乡收入比收敛年数（约12-15年）",
             "params": {"results": [{"label": "收敛年数", "expected": 13, "tolerance": 3}]}},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算额外释放消费",
             "params": {"results": [{"label": "额外消费", "expected": 1789, "tolerance": 100}]}},
            {"type": "soft", "description": "恩格尔系数阶段判断正确",
             "rubric": "恩格尔系数32%处于'富裕'阶段（30%-40%区间），接近'最富裕'标准（<30%）"},
        ])

    add("T3.3-006", CTX_REALESTATE,
        """请基于以上房地产数据，进行以下高阶推导：

1. 新建商品房全国均价 = 销售额/销售面积，计算一季度均价和同比变化率
   （提示：销售面积降10.4%、销售额降16.7%，由此推导均价变化）
2. 住宅待售面积42771万m²，按当前季度销售速度（16008万m²/季），计算去化周期
3. 到位资金/开发投资 = 资金覆盖倍数。如果到位资金继续按17.3%下降，投资按11.2%下降，一年后覆盖倍数如何变化？
4. 东北投资仅196亿元、销售额仅385亿元，推算东北房地产市场规模占全国的比重

输出要求：使用Markdown格式，展示详细推导过程和公式。""",
        [
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算均价同比变化率",
             "params": {"results": [{"label": "均价变化率", "expected": -7.0, "tolerance": 1.0}]}},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算去化周期",
             "params": {"results": [{"label": "去化周期", "expected": 2.67, "tolerance": 0.2}]}},
            {"type": "hard", "checker": "check_computation_result",
             "description": "正确计算东北投资占比",
             "params": {"results": [{"label": "东北投资占比", "expected": 1.1, "tolerance": 0.2}]}},
            {"type": "soft", "description": "资金覆盖倍数推导逻辑正确",
             "rubric": "应展示当前覆盖倍数1.16，一年后基于各自降幅推导新的覆盖倍数，约为1.16×(1-0.173)/(1-0.112)≈1.08"},
        ])

    return cases, constraints


# ─── 主函数 ─────────────────────────────────────────────────────

def main():
    # 备份原文件
    for path in [BENCHMARK_PATH, EVALCONFIG_PATH]:
        backup = path + ".bak_pre_expand"
        if not os.path.exists(backup):
            shutil.copy2(path, backup)
            print(f"Backup: {path} → {backup}")

    # 加载现有数据
    with open(BENCHMARK_PATH, encoding="utf-8") as f:
        benchmark = json.load(f)
    with open(EVALCONFIG_PATH, encoding="utf-8") as f:
        evalconfig = json.load(f)

    existing_cases = benchmark["cases"]
    existing_constraints = evalconfig["constraints"]

    print(f"Existing: {len(existing_cases)} cases, {len(existing_constraints)} constraints")

    # 加载 batch1 文档
    batch1_docs = load_batch1()
    print(f"Loaded {len(batch1_docs)} batch1 documents")

    # 生成新 cases 和 constraints
    new_cases, new_constraints = build_new_cases(batch1_docs)
    print(f"Generated: {len(new_cases)} new cases, {len(new_constraints)} new constraints")

    # 检查 case_id 冲突
    existing_ids = {c["case_id"] for c in existing_cases}
    new_ids = {c["case_id"] for c in new_cases}
    conflicts = existing_ids & new_ids
    if conflicts:
        print(f"ERROR: case_id conflicts: {conflicts}")
        return

    # 合并
    benchmark["cases"] = existing_cases + new_cases
    evalconfig["constraints"].update(new_constraints)

    # 写入
    with open(BENCHMARK_PATH, "w", encoding="utf-8") as f:
        json.dump(benchmark, f, ensure_ascii=False, indent=2)

    with open(EVALCONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(evalconfig, f, ensure_ascii=False, indent=2)

    total_cases = len(benchmark["cases"])
    total_constraints = len(evalconfig["constraints"])
    print(f"\nResult: {total_cases} cases, {total_constraints} constraints")
    print(f"  → {BENCHMARK_PATH}")
    print(f"  → {EVALCONFIG_PATH}")

    # 统计
    l2_counter = Counter(c["case_id"].rsplit("-", 1)[0] for c in benchmark["cases"])
    print(f"\nL2 distribution:")
    for k, v in sorted(l2_counter.items()):
        print(f"  {k}: {v}")

    # 统计约束类型
    hard = sum(1 for v in evalconfig["constraints"].values() if v["type"] == "hard")
    soft = sum(1 for v in evalconfig["constraints"].values() if v["type"] == "soft")
    print(f"\nConstraints: {hard} hard + {soft} soft = {total_constraints}")


if __name__ == "__main__":
    main()
