# Hard300 Swap Top50 Final

筛选规则：
- `50 in`：来自 `train764`，GPT-5 未 exact pass，优先 `DB7 / DB9 / QV2 / QV5 / QV6`，不收纯 `EG2`，剔除明显 `FP2/FP3` 污染与已知 prompt 冲突样本。
- `50 out`：来自当前 `hard300` 的 `GPT-5 exact pass`，优先标签结构通用、重复度高、代表性增量弱的题，不动 `DB8 / QV4 / RC4 / DB1 / DB2` 长尾锚点。

- `50 in` 数量：`50`
- `50 out` 数量：`50`
- `50 in` priority tags：`{'DB7': 28, 'DB9': 20, 'QV2': 13, 'QV5': 9, 'QV6': 1}`
- `50 out` semantic tags：`{'DB9': 50, 'EG2': 50, 'QV2': 50, 'EG1': 46, 'DB4': 37, 'EG5': 28, 'DB6': 14, 'DB7': 12, 'QV6': 7, 'EG3': 5}`
- `50 in` workflow：`{'Decision and Structuring': 14, 'Execution, Monitoring, Reporting, and Operations': 10, 'Intake and Profiling': 8, 'Risk and Compliance Review': 14, 'Research and Due Diligence': 4}`
- `50 out` workflow：`{'Execution, Monitoring, Reporting, and Operations': 14, 'Intake and Profiling': 11, 'Risk and Compliance Review': 12, 'Research and Due Diligence': 7, 'Decision and Structuring': 6}`

文件：
- `outputs/reports/hard300_swap_in_top50_final_20260616.csv`
- `outputs/reports/hard300_swap_out_top50_final_20260616.csv`