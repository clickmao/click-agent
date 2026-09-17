# R543 · 用例面归档（RF0001 精简轮）

日期：2026-09-18 ｜ 装置：`tools/archive/archive_cases.py` ｜ 归档面：`eval/archive/cases/**`

## 1. 因果链

用户令「继续下轮，不需要的用例全部归档，只留经典用例」 ⇒「经典」必须有**机检判据**，否则归档就是拍脑袋：

- 判据 = 保留面 = **白名单（经典判定面）∪ 可执行闭包 ∪ 通配扫描保护**。
- 未定义「经典」的代价（本轮实证，负控 N2）：`eval/bge/fixtures/corpus.jsonl` 与 `eval/recall/r487/corpus-list-r487.json` 这类**语料**里出现 100+ 个仓内路径字符串 —— 若把「文本里出现路径」当引用，几乎所有用例都会被误判为「被引用」。⇒ 只有**可执行文件**（`.py/.cs/.sh/.ps1/.js` 或 shebang 脚本）才能展开引用，数据文件是叶子。

## 2. 保留规则（机检 · fail-closed）

| # | 规则 | 语义 |
|---|---|---|
| K1 | 白名单 | 主线判定面：`rover/{lib,r507pre,r510,r536,r539,r540,r541,r542}`、`capability/exp1-q51`、`capability/status.py`、KPI 挂钩器具；另含前序轮封存清单里点名的「现行可运行链」轮次（`r371d7/r413/r415/r455/r483/r511/r512/r517/r520/r527/r531/r532/r533/r535` 等）与 `eval/bge/`（在飞：工作树有未提交改动） |
| K2 | 机器台账 | `docs/verification-registry.json`、`eval/capability/kpi.jsonl`、`instruments.json` 引用的路径**必须现盘存在** ⇒ 一律留原位（机检 R2/R2b/R2c 不变） |
| K3 | 可执行闭包 | 从 `src/**`·`tools/**`·`scripts/**`·`tools/hooks/pre-commit` 出发**不动点**展开；只从可执行文件展开；唯一 basename 兜底（`Path.Combine("eval","x.json")` 形式） |
| K4 | 通配保护 | 形如 `eval/rover/*/verdict*.json` 的模式按**模式命中**保护文件；「整个面」的退化模式（`eval/**`）不构成保护，否则一句目录提及就钉死全仓 |
| K5 | 自排除 | `eval/archive/**` 不参与候选（探针产物必自排除） |

## 3. 读数

| 面 | 归档前 | 归档后 |
|---|---|---|
| `eval` 活跃面文件 | 3,846 | **3,055**（+归档 791） |
| 归档条目 | — | **791**（`AC-0001..AC-0791`）|
| 归档行数 / 字节 | — | **296,097 行 / 10.65 MiB** |
| 分布 | — | results 542 · capability 218 · dcr 10 · rover 5 · README.md 1 · analyze.py 1 · cross_validate.py 1 · explore_eval.py 1 · k1-behavior-cases.json 1 · k1_behavior.py 1 · k1_diff.py 1 · kpi 1 · multi_turn_driver.py 1 · phase_report.py 1 · probe 1 · recall 1 · recall_report.py 1 · tmp-link-audit.json 1 · token_report.py 1 · vulkan 1 |
| KPI/registry 引用面 | 1,408 条 | **1,408 条（全部留原位，0 条入档）** |
| 活文档引用重写 | — | README.md、`docs/plans/v0.22.0-exp1-local-index-and-code-graph.md` |
| 空目录补 `.gitkeep` | — | 7 |

## 4. 机检（全部真跑）

| 检查 | 命令 | 读数 |
|---|---|---|
| 器具自检 | `python3 tools/archive/archive_cases.py --selftest` | **PASS**：正控 3（判定面在 KEEP / 钩子机检器在 KEEP / 候选不越界到 src·tools·scripts·docs）· 负控 4（台账不误档 · 数据叶子不误判 · 归档面自排除 · 规模非退化）|
| 归档校验 | `... --verify` | **PASS**：覆盖 100% · sha 一致 · 无悬空引用 · 索引=台账 |
| 可逆 | `... --restore` | 按台账 `now→orig` 反向 `git mv`（本轮未触发） |

## 5. 诚实边界

0. **激进口径已被实测证伪**：不护「活面点名的目录」时候选 1,905 文件 ⇒ 全量 **3 红**（`SessionHistorySearchTests.R423_FrozenCorpus_FeatureVector_IsMachinePinned_NotHandCounted` 等读 `eval/capability/r422/fixture-sessions`）⇒ 采保守口径 **791**（失败读数即判据，非事后补 `require` 收窄）。

1. **归档 ≠ 删行**：文件在仓内迁移（`git mv`），全仓行数不变；只有**活跃面**缩小（`eval` 3,846→1,941 文件）。
2. 本轮的「经典」是**机检判据**下的定义（白名单 ∪ 闭包），不等于「人类认为重要的全部用例」。凡被 KPI 表/registry/起手闸/契约机检器引用者一律保留。
3. 前序兄弟会话留有未提交的 `eval/rover` 封存草案（`eval/rover/ARCHIVE.md` + `/home/agentuser/af-archive/rover-archive-20260918.tar.gz`，含 64 轮方案）；**该方案未被提交、其 64 轮并未从索引移除**（HEAD 仍有 102 个轮目录）⇒ 本轮按本装置规则统一判定，不与其冲突，亦不代其声明。
4. 未闭合：`g1` 43/58 · codex 外侧列 rc=1 · role 无增益（与 R542 同）；本轮不改变任何能力读数。
