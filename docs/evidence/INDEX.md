# 证据索引（人读 · RF 版本线）

> 机器台账（权威）：`docs/verification-registry.json`（能力 × 验证级）+ `eval/capability/kpi.jsonl`（逐轮 KPI 行）。
> 本文件只做**人读导航**：版本 → 能力 → KPI → 证据指针。规范见 `README.md`（同目录）。

| 版本 | 计划 | KPI（实测/口径） | 证据 | 状态 |
|---|---|---|---|---|
| **RF0001** | `docs/plans/RF0001-fable-aligned-development-plan.md` | `RF0001/KPI.md`：缓存命中 **97.37%**（≥97% 达标）· 调用 Δ **93.9–97.1%** · token Δ **96.1–98.1%** · 前端条目事件 **0→4** | `RF0001/EVIDENCE.md`（E01–E09，逐条可复现命令） | 交付中（R541 起）；**未闭合**：`g1` 43/58 · codex 外侧列 rc=1 · role 无增益 |
| RF0002 | *待开（识别侧路：LFM2.5-VL-3B / 屏幕识别 / 视频学习 / 特征库快路径）* | — | — | 顺延（用户令：识别先不做） |

## 归档面（旧版本线）
| 面 | 指针 | 读数 |
|---|---|---|
| 归档台账（机读） | `../archive/archive-registry.json` | 216 条 `AR-####`，含 `sha256_orig`/`sha256_now`/`keep_reason`/`base_commit` |
| 归档索引（人读） | `../archive/ARCHIVE-INDEX.md` | 216 行（plans 110 / reports 93 / changelogs 13），21,282 行 |
| 机检 | `python3 tools/archive/archive_docs.py --verify` | PASS：覆盖 100% · 无悬空引用 · DocRef 全解析 · 索引=台账 |

## 保留面（不入档，仍在原位）
当前功能描述与活台账：`README.md`/`README_EN.md`、`docs/api.md`、`docs/architecture.md`、`docs/CLI指令说明.md`、`docs/Role使用说明.md`、`docs/Skill全局通用开发规范.md`、`docs/验证形式规范.md`、
`docs/api-surface.baseline.txt`、`docs/verification-registry.json`、`docs/improvements.md`、`docs/external-reference*/**`、
`docs/reports/{iteration-master-plan,dynamic-telemetry-eval-rollback-strategy,test-dimensions-ledger,dev-return-digest,endpoint-and-audit-contract,status.json,round-collision-log.jsonl,bge/**}`、
以及被 `src/**`·`tools/**`·`scripts/**`·`config/**` 硬引用的 14 份历史文档（理由逐条见台账 `keep_reason`）。
