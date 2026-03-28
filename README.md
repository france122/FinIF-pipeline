# paper_for_financial_if_benchmark

中文金融垂类 Instruction Following Benchmark 的数据与脚本仓库。

当前仓库主要保存三类内容：

- `FIFE` 中文化模板与 `CFinBench` 角色映射文档
- `query pool v2` 的生成脚本与生成结果
- `ID held-out` 划分后的 `V / NV / Mixed` track 数据

## 目录结构

```text
paper_for_financial_if_benchmark/
├── README.md
├── docs/
│   ├── constraint_pool.md
│   ├── FIFE_template_candidates.md
│   └── CFinBench_role_mapping.md
├── scripts/
│   ├── generate_query_pool_v2.py
│   └── build_id_heldout_tracks.py
├── data/
│   ├── fineval_raw/
│   │   ├── industry/
│   │   │   ├── finsuggestion-eval.json
│   │   │   └── finsales-eval.json
│   │   └── agent/
│   │       ├── findiag-eval.json
│   │       └── apiutil-eval.json
│   ├── query_pool/
│   │   └── query_pool_v2_final.json
│   ├── splits/
│   │   ├── id_heldout_train_queries.json
│   │   └── id_heldout_test_queries.json
│   └── tracks/
│       ├── id_heldout_v_track.json
│       ├── id_heldout_nv_track.json
│       ├── id_heldout_mixed_track.json
│       └── id_heldout_all_tracks.json
└── viewer/
    ├── query_pool_v2_viewer.html
    └── id_heldout_tracks_viewer.html
```

## 当前数据状态

### Query Pool v2

- 总量：`1000` 条 query
- `FinEval` 原题：`112`
  - `finsuggestion` 28
  - `findiag` 27
  - `apiutil` 27
  - `finsales` 30
- `FIFE` 中文化模板生成题：`888`
  - `T1` / `T2` / `T4` / `T5` / `T7` / `T9` / `T10` / `T11`
  - 每个模板 111 条
- 角色增强：
  - `with_role` 333
  - `no_role` 667

### ID Held-out 划分

- `train-query`：`800`
- `test-query`：`200`

### Track 样本

- `V-track`：`1000`
- `NV-track`：`1000`
- `Mixed-track`：`1000`
- 总样本数：`3000`

## 数据构造思路

### Query 构造

1. 从 `FinEval` 中保留 4 类开放性较强的原始题：
   - `finsuggestion`
   - `findiag`
   - `apiutil`
   - `finsales`
2. 从 `FIFE` 中抽取可迁移的开放式任务模板，并做中文金融语境改写
3. 将 `CFinBench` 作为角色/岗位/语境词典，用于给部分 query 注入角色信息
4. 角色只作为 query 层增强变量，不作为 constraint

### 划分与 track 构造

- 先做 `query` 级别的 `80/20` 划分，再混合 `constraint`
- 避免同一条 query 的不同约束版本同时出现在训练集和测试集
- 当前只构造一个主测试集，定位为 `in-domain held-out`

## 约束规则

约束池定义见：

- `docs/constraint_pool.md`

当前 track 构造规则：

- `V-track`：每条样本混 `1-3` 个 V constraint
- `NV-track`：每条样本混 `1-3` 个 NV constraint
- `Mixed-track`：以 `1V + 1NV` 为主，少量 `2V + 1NV`
- 组合方式为：先按规则筛候选，再随机抽样
- 当前显式排除了互斥约束对 `FN-7 / FN-8`

## 脚本说明

### 1. 生成 query pool v2

```bash
python scripts/generate_query_pool_v2.py
```

输出：

- `data/query_pool/query_pool_v2_final.json`
- `viewer/query_pool_v2_viewer.html`

### 2. 生成 ID held-out 划分与三类 track

```bash
python scripts/build_id_heldout_tracks.py
```

输出：

- `data/splits/id_heldout_train_queries.json`
- `data/splits/id_heldout_test_queries.json`
- `data/tracks/id_heldout_v_track.json`
- `data/tracks/id_heldout_nv_track.json`
- `data/tracks/id_heldout_mixed_track.json`
- `data/tracks/id_heldout_all_tracks.json`
- `viewer/id_heldout_tracks_viewer.html`

## Viewer

仓库中保留了两个本地 HTML 检查页：

- `viewer/query_pool_v2_viewer.html`
- `viewer/id_heldout_tracks_viewer.html`

这两个文件均为独立页面，可直接本地打开查看。
