请为以下 query 选择约束并参数化。

## 配置

- track_type: {track_type}
- 需要选择的 Hard 约束数量: {n_hard}
- 需要选择的 Soft 约束数量: {n_soft}

## Query

query_id: {query_id}

{query_text}

## 要求

从约束池中选择 {n_hard} 个 Hard 约束（GH/FH）和 {n_soft} 个 Soft 约束（GS/FS），使其与上述 query 语义适配。对含参数的约束进行参数化填充。遵守互斥规则。严格输出 JSON。
