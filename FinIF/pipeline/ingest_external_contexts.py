#!/usr/bin/env python3
"""
从 raw_contexts_batch1 目录读取真实金融文档（PDF/MD），
清洗文本、提取关键数值，输出 context_pool_external.jsonl。

格式与 context_pool.jsonl 对齐，source="external"。
"""
import json, os, re, glob

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(os.path.dirname(os.path.dirname(PIPELINE_DIR)), "raw_contexts_batch1")

DOC_META = {
    "减持公告.pdf":                        {"L1": "T1", "L2": "T1.2", "tag": "减持公告"},
    "股票交易风险提示公告.pdf":            {"L1": "T1", "L2": "T1.1", "tag": "风险提示"},
    "股票交易风险提示公告2.pdf":           {"L1": "T1", "L2": "T1.1", "tag": "风险提示"},
    "问询函.pdf":                          {"L1": "T2", "L2": "T2.1", "tag": "问询函"},
    "问询函2.pdf":                         {"L1": "T2", "L2": "T2.1", "tag": "问询函"},
    "问询函3.pdf":                         {"L1": "T1", "L2": "T1.2", "tag": "问询函"},
    "2025*ST恒久年度报告.pdf":             {"L1": "T2", "L2": "T2.2", "tag": "年报摘要"},
    "中国证监会行政处罚决定书（惠程科技）_中国证券监督管理委员会.pdf":
        {"L1": "T1", "L2": "T1.3", "tag": "行政处罚"},
    "中国证监会行政处罚决定书（刘惠忠）_中国证券监督管理委员会.pdf":
        {"L1": "T3", "L2": "T3.2", "tag": "行政处罚"},
    "中国证监会行政处罚决定书（涂尔帆）_中国证券监督管理委员会.pdf":
        {"L1": "T3", "L2": "T3.1", "tag": "行政处罚"},
    "中国证监会市场禁入决定书（吴光胜）_中国证券监督管理委员会.pdf":
        {"L1": "T3", "L2": "T3.2", "tag": "市场禁入"},
    "中国证监会市场禁入决定书（张志勇）_中国证券监督管理委员会.pdf":
        {"L1": "T3", "L2": "T3.1", "tag": "市场禁入"},
    "最高人民法院发布造假典型案例.md":     {"L1": "T3", "L2": "T3.2", "tag": "司法案例"},
}


def read_pdf(path):
    from pypdf import PdfReader
    reader = PdfReader(path)
    pages = []
    for p in reader.pages:
        t = p.extract_text()
        if t:
            pages.append(t)
    return "\n".join(pages)


def read_md(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def clean_text(raw):
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
        if re.match(r'^(首页|登录|注册|网站地图|联系我们|版权所有|ICP备)', line):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def extract_numbers(text):
    """提取文本中的关键数值对 {label: value}"""
    values = {}
    pats = [
        r'([一-鿿]{2,10}(?:为|达|约|共计|合计|共|累计))\s*([-+]?[\d,]+\.?\d*)\s*(万元|亿元|万股|%|％|元)',
        r'([一-鿿]{2,8})[：:]\s*([-+]?[\d,]+\.?\d*)\s*(万元|亿元|万股|%|％|元)',
        r'\|\s*([一-鿿]{2,10})\s*\|\s*([-+]?[\d,]+\.?\d*)\s*(万元|亿元|%|％|元)?\s*\|',
        # 宽松模式：中文词 + 空白 + 数值 + 单位
        r'([一-鿿]{2,6})\s+([-+]?[\d,]+\.?\d*)\s*(万元|亿元|万股|%|％)',
        # "不超过 13,600,000 股" → label=前面的动宾短语
        r'([一-鿿]{2,8})\s*([\d,]{4,})\s*(股|万元|亿元|元)',
        # 百分比紧跟数字: "6.39%"
        r'([一-鿿]{2,8}(?:比例|占比|持股))[^\d]{0,5}([\d.]+)\s*(%|％)',
    ]
    for pat in pats:
        for m in re.finditer(pat, text):
            label = m.group(1).strip()
            val = m.group(2).replace(',', '')
            unit = m.group(3) if m.lastindex >= 3 and m.group(3) else ""
            if label and val and len(val) >= 1:
                values[label] = val + unit
            if len(values) >= 15:
                break
        if len(values) >= 15:
            break
    return values


def main():
    output_path = os.path.join(PIPELINE_DIR, "data", "context_pool_external.jsonl")
    records = []
    idx = 0

    for fname, meta in DOC_META.items():
        fpath = os.path.join(RAW_DIR, fname)
        if not os.path.exists(fpath):
            # 处理通配符文件名 (如 2025*ST恒久)
            matches = glob.glob(os.path.join(RAW_DIR, fname))
            if matches:
                fpath = matches[0]
            else:
                print(f"  SKIP (not found): {fname}")
                continue

        if fname.endswith(".pdf"):
            raw = read_pdf(fpath)
        else:
            raw = read_md(fpath)

        text = clean_text(raw)
        if len(text) < 100:
            print(f"  SKIP (too short after clean): {fname}")
            continue

        # 截断过长文档，保留前 6000 字符
        if len(text) > 6000:
            text = text[:6000]

        idx += 1
        case_id = f"EXT-{meta['L2']}-{idx:03d}"
        values = extract_numbers(text)

        rec = {
            "context_id": f"CTX-{case_id}",
            "case_id": case_id,
            "L1": meta["L1"],
            "L2": meta["L2"],
            "source": "external",
            "tag": meta["tag"],
            "text": text,
            "query": "",
            "char_count": len(text),
            "extracted_values": values,
            "computable_relations": [],
        }
        records.append(rec)
        print(f"  OK: {fname} → {case_id} ({len(text)} chars, {len(values)} values)")

    with open(output_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\nTotal: {len(records)} external contexts → {output_path}")


if __name__ == "__main__":
    main()
