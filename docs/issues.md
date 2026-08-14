# Research Output Issues

## Issues

| # | item | type | severity | description |
|---|---|---|---|---|
| 1 | All 11 planned workbooks | table | minor | The main worksheets contain formulas without cached results. The authoritative local previews therefore return missing values in at least one planned field for every workbook, although the visible LibreOffice previews recalculate correctly. This machine-readability limitation has been accepted as non-blocking, conditional on verifying table values during manuscript ingestion. |

## Severity Summary

| severity | count |
|---|---|
| critical | 0 |
| major | 0 |
| minor | 1 |

## Recommended Next Steps

- 公式缓存限制已经用户接受，不阻塞后续工作；在论文导入表格时，应核对工作簿重新计算后的显示值与分析脚本结果，若导入工具无法稳定读取，再返回 `figure-table-generation` 生成静态值版本。
- 当前仅剩 minor 问题，可以继续 `build-content-dictionary`。
