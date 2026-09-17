# RF0001 · EVIDENCE（逐条证据指针）

规则：每条 = 断言 + 验证级（L0–L4）+ **可复现命令** + 产物指针 + 归属轮次/提交。
产物本体在 `eval/**`（受 L3 闸护，不搬动）；`/tmp` 下的探针原始输出随会话销毁，故此处只留**仓内可复现**命令。

| id | 断言 | 级 | 复现命令 | 产物 / 指针 | 轮次·提交 |
|---|---|---|---|---|---|
| RF0001-E01 | 恒定前缀逐字节恒定且被钉（字符 14,863 / 最小 6,704 tok 门） | L1 | `python3 tools/r1gen/r1prompt.py` ∧ `python3 tools/r1gen/gen_csharp.py --check` | `src/agent/contract/StructuredPrompt.cs`：`PrefixChars=14863`、`PrefixMinTokensForCache97=6704`、`PrefixSha256Pinned=ed13dd23577db89323b5263def755512baf4e640e0783b4ee2df32dcc8fa7637` | R537 `1aac63b` |
| RF0001-E02 | 前缀缓存命中 ≥97%（前缀复用口径） | L3 | 真跑 + `eval/capability/kpi.jsonl` 对应 `round` 行 | kpi 行 `R537`：prefix 6,704 tok / hit 6,528 / miss 176 ⇒ 0.9737 | R537 `1aac63b` |
| RF0001-E03 | 前端条目面事件真发（`item.started`/`item.completed`）+ 快照 `last_item` | L3 | `eval/rover/r510/run_e2e_frontend_progress.sh` + `assert_e2e_progress.py` | 同探针 AOT 真跑：事件 7→11、`item.*` 0/0→2/2、`task.progress` 载荷 6 键逐字节同 | R538 `84d8bc0` |
| RF0001-E04 | 展示文案主参数键与工具 schema 同源（真跑抓出 `command`≠`cmd`） | L2 | `dotnet test src/agent.tests --filter FullyQualifiedName~R538` | `src/agent.tests/R538FrontendItemEventsTests.cs` | R538 `84d8bc0` |
| RF0001-E05 | `R1r` vs `A1-on` 同题同窗：调用 Δ93.9/97.1%、token Δ96.1/98.1%，质量不降 | L3+L4 | `eval/rover/r540/run_r540.sh`（外侧臂经 `eval/rover/lib/codex_engine.py` 加载） | `eval/rover/r540/evidence/**`；kpi 行 `R540` | R540 |
| RF0001-E06 | 缺信息 ⇒ 停链（rc=2·steps=0·工作区 0 文件） | L3 | `python3 eval/rover/r539/check_ms1_zero_side_effect.py` | `eval/rover/r539/**` | R539 `71f6d8b` |
| RF0001-E07 | rc=8 成对报（自测未达成 + 产物可疑）+ `correctness_asserted` 仅 rc=0 为 1 | L2 | `python3 eval/rover/r539/rc8_evidence_guard.py` | `src/agent/r1/R1Transcript.cs`（新字段）、机检 13 transcript/16 快照行 PASS | R539 `71f6d8b` |
| RF0001-E08 | 外侧引擎 fail-closed 加载 + 减法批删除前查调用点 | L1 | `python3 eval/rover/lib/codex_engine.py --selftest` ∧ `python3 tools/refactor/delete_ref_gate.py --selftest` | 6 正控+2 负控全绿；`git grep codex_solver_r504` 残留 0 | R540 |
| RF0001-E09 | 全量回归不降 | L2 | `dotnet test agent.sln -c Release` | **1858/1858** 绿（API 面 +1/−0 显式重生） | R540 |
| RF0001-E10 | 验收前置器（铁律 11） | L3 | `python3 eval/rover/r507pre/exec_precondition.py --round r540` | **rc=1**（阻塞 = `g1` 43/58·44/58）⇒ 降幅标「参考（未可验收）」 | R540 |
| RF0001-E11 | 归档面无悬空引用、台账 100% 覆盖 | L1 | `python3 tools/archive/archive_docs.py --verify` | `docs/archive/ARCHIVE-INDEX.md` + `archive-registry.json` | R541 |

> **未闭合（不得当作通过）**：E05/E10 的降幅因 rc=1 仅为参考；`g1` 族未闭合；codex 外部列单窗不可比；
> role 挂载未证增益；`A1-on` 在 `g1` 上无基线。
