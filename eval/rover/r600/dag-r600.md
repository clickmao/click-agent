# R600 · DAG（产品侧修复：回灌修复环「带现状」）

用户令 2026-09-20「放行」⇒ 产品源码可动。单变量 = `AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER`。

## 节点与依赖

| # | 节点 | 依赖 | 并行面 | 判据/产出 |
|---|---|---|---|---|
| N1 | 只读定因（失败臂产物在题面公开用例上即失败 + 管道已回放已修复仍同错类） | — | 与 N2 前置并行 | `eval/rover/r600/` 定因读数（本轮 prereg.why_now） |
| N2 | 产品改动：`ArtifactCarryover.cs`（新件）+ `R1Options` 新轴（缺省 on）+ `R1Pipeline` 两处接线（探针修复/执行修复） | N1 | — | 源码 diff：仅 3 文件 + 新单测 |
| N3 | 定向单测 + build + 全量 + 形式门禁 + API 基线重生（`BASELINE_WRITE=1`，差异仅本轮行） | N2 | 与 N4 前置并行不可（N4 依赖 N2/N3 通过） | 全量 rc=0；形式 14/14 |
| N4 | AOT 发布 `pub_r600/agenthost` + 零 IL 核验（发布形态铁律：发布必 AOT） | N3 | — | `bin_sha12_measured` 回填 + IL 面为空 |
| N5 | 真机 A/B：3 窗 × (T×3 + C×3 + C1×1) | N4 | **T/C/C1 三档可并行起臂**（唯一串行约束：llama-server 只一个；本轮各臂只用远端 LLM + codex，不占本地 llama） | 每跑次：探针 marker + steps + 终端 rc/stage + calls/prompt token |
| N6 | 判据 v3 + J1–J4 读数 + KPI 表 + 证据档 + registry + 提交（逐名 `git add`） | N5 | 读数与文档落盘并行 | `verdict-r600.json` / `kpi-table-r600.json` / `report-r600.md` |
| N7 | 恢复 cron tick（本轮起手前已 pause，防同仓双写） | N6 | — | tick `enabled=true` |

## 重启判据（收尾时判「重启哪条边」）

- N4 失败（AOT 黑）⇒ 重启 N3（JIT 面），N5 不起（不起臂）。
- N5 中任一档出现「探针 marker 缺失 / key 面未自备 / 起手闸余量 < 2650MB」⇒ 该跑次标 `unreliable` 并**只重跑该跑次**（不重跑整档）。
- N5 全档完成后 J1 反例（对照档出现 carryover 打点）⇒ 机制面判废，N6 只落负结论，不宣称达标。
- 跨轮只并列不相减（窗集不同 + 被测件按设计变更 ⇒ 与被测件冻结轮不可减）。
