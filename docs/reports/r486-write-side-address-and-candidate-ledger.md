# R486 · 并轮令落盘 + 写侧地址有效性诊断 + 空正文差分器具（staged）

状态: 完成（器具已预注册；形式门禁 14/14 绿、全量 1540/1540、已提交）
轮次: R486（本会话）／ R485（对侧 cron:9a97763d5fcd 并行，见 §3）
DocRef: eval/rover/r486/prereg_r486.json

## 1 · 用户令落盘（并轮）

| 项 | 落盘位置 | 证据 |
|---|---|---|
| 「所有候选并入一轮解决」（原「只推进一步」措辞作废） | cron 作业 `9a97763d5fcd`(30m) 与 `b15eb2f40a69`(60m) 的 prompt | `hermes cron edit --prompt` 执行后回读 `~/.hermes/cron/jobs.json`，两处「一步」措辞计数 = 0 |
| 同上（长期记忆） | `~/.hermes/memories/MEMORY.md` | 条目「全候选并轮令(2026-09-16 用户钦定)」 |

## 2 · 写侧地址有效性诊断（本轮新增读数）

器具: `eval/recall/r486/write_side_address_probe.py`（只读仓库文本；语言无关；三态 rc=0/1/3；`--nc-perturb` 负控；自污染闸：自身产物目录不入语料）
读数: `eval/recall/r486/write-side.json`（corpus = 834 个 .md/.txt，`files_sha16=1494490dc1586faf`）

| 分面 | 数量 | 占比 |
|---|---|---|
| 路径引用（去 scheme、去纯锚点） | 87 | 100% |
| 可解析（含目录） | 79 | 90.8% |
| 写侧路径误写（同名文件存在于仓库他处） | 5 | 5.7% |
| 从未写出（全仓库无此名） | 3 | 3.4% |
| 越根 escape | 0 | 0 |
| scheme 地址（单列 unreported） | 12 | — |
| 纯锚点/省略号（不进分母） | 33 | — |

- 守恒 `87 = 79 + 5 + 3 + 0` ✔；负控 `--nc-perturb` ⇒ resolved=0 / never_written=83（判据翻面）✔ fail-closed。
- **5 条「误写」全在 `docs/improvements.md`**：写成根相对（`docs/验证形式规范.md`）却被按引用方目录解析 ⇒ 渲染即断链，属写侧可修（改成 `./验证形式规范.md` 或 `../...`）。
- 3 条「从未写出」中 ≥2 条是正则假阳（省略号 `[…]`、字面 `url`）⇒ 写侧真实缺失 ≈ 1（`docs/changelogs/` 目录不存在）。
- 结论（对 R483 分档的补充）：markdown 档 0.8125 的悬空里，**写侧路径写法**占主导，不是解析器缺能力；修法优先级 = 写侧规范/回填，而非解析侧放宽。

## 3 · 撞车与还原（namespace clobber）

- 事实: 09:51:26 对侧（cron:9a97763d5fcd，R485）落盘 `eval/rover/r485/prereg_r485.json`（4,882 B）；本会话 09:53:27 误向同路径写入自己的 R485 预注册 ⇒ 覆盖。
- 还原: 从会话库 `state.db`（messages.id=148636 的 write_file 调用）逐字节还原对侧原文 ⇒ **4,882 B / sha256 `ddea5c3116de0ae9…`**，与对侧 `bytes_written=4882` 一致。
- 本侧让行: 轮号改 **R486**；未触碰 `eval/rover/r485/` 其余文件；对侧同刻在跑 `dotnet build src/agent/agent.csproj`。
- 记录: `docs/reports/round-collision-log.jsonl` 第 5 行（键集与既有 4 行一致，全部行可 JSON 解析）。
- 预防: 起手前先 `ls -la` 目标轮目录并看 mtime；目录已存在且有对侧写入 ⇒ 换轮号。

## 4 · 空正文（带 tool_calls）浪费重试差分 —— 器具 staged，真跑受阻

- 目的: R482 真机 H3/H4 FAIL 的成因是上游空正文基数漂移（15→4），使「可省调用」不可测；本器具把该面搬到确定性桩上，直测「修复是否消除每次空正文事件的 1 次浪费远端调用」。
- 已落盘（先于任何测量）: `eval/rover/r486/{prereg_r486.json, stub_upstream_r486.py, task-r486.json, run_diff_r486.sh, check_r486.py}`。预注册 H1（`pre−post==1`，主判据）/H2/H3/H4/NC1（plain 模式两侧相等）。
- 判据器自检（影子目录 `/tmp/r486_selftest`，产物目录无伪数据）: PASS 用例 rc=0；无差分 ⇒ FAIL(H1,H2)；负控不等 ⇒ FAIL(NC1)；pre 侧未重试 ⇒ FAIL(H4)。**自检抓到首版 H4 把 pre/post 遥测写反的实缺陷** ⇒ 改代码对齐预注册陈述（禁改断言）。
- **受阻原因（未测，不冒充）**: 起手闸 `MemAvailable=2134MB < 2650MB`，且对侧会话正在 `dotnet build` ⇒ 依「对侧活跃则本侧不跑测量」纪律让行。`run_diff_r486.sh` 内建双闸（内存 ∧ dotnet 热进程）⇒ 拒跑 rc=10/11。

## 5 · 候选台账（逐项：做／未做 + 原因）

| # | 候选 | 状态 | 原因 |
|---|---|---|---|
| 1 | 空正文浪费重试可测化差分 | 器具完成、真跑未做 | 起手闸红 + 对侧 dotnet 在跑（§4） |
| 2 | 微问询形态分流（指代词微问询不发） | 未做（对侧在做） | 对侧 R485 预注册明示「先于新 AOT 发布」⇒ 避免同题双写 |
| 3 | 禁常量兜底臂真跑（11.78% 代理换实测） | 未做 | 需真机窗口 + 凭据 + llama-server（2.4GB）；当前闸红 |
| 4 | **写侧地址有效性机检** | **本轮已做**（§2） | — |
| 5 | blocker_cause 双标（内存∧进程并存） | 未做 | 目标器具 `eval/rover/r484/preflight_gate.py` 为对侧热文件 |
| 6 | R479 遗留（路由器接线 / 入链 prompt 正文槽位化） | 未做 | 需 dotnet 窗口；对侧在跑 build |
| 7 | EXP1 侧候选（`bind_evidence --only` 等） | 未动 | 属自检作业自有命名段，避免跨写者 |
| 8 | 修 `docs/improvements.md` 5 条根相对断链 | 未做（已定位） | 该文档为对侧热文件，留待无写者窗口 |

## 5.1 · 门禁与提交状态（本回合）

- 形式门禁（`VerificationFormTests|DevPlanDocRefTests|SkillGeneralizationTests`）：**已跑，绿**。R492 窗内对侧退场后补跑（`eval/rover/r486/gates_r486.sh`，2026-09-16 17:1x）：**执行数=14 / Failed=0**（执行数>0 断言过 ⇒ 非假绿）；全量单测 **1540/1540**。
  - 历史 BLOCKED 原因（留档）：等对侧 dotnet 退场 240 s 仍未清（终态 `MSBuild/VBCSCompiler hot=2`，`MemAvailable=2081MB < 2650MB`）⇒ 依纪律不抢跑、不抢开关（`build-server shutdown` 会打断对侧构建）。
- 本轮产物：`eval/rover/r486/*`、`eval/recall/r486/*`、本报告、`round-collision-log.jsonl` 第 5 行 —— 门禁转绿后随窗提交。

## 6 · 诚实边界

- 写侧诊断是**独立正则口径**（非 R481-F 源码派生端口），只覆盖 `.md/.txt` 文档面 834 文件；`never_written` 含 ≥2 条正则假阳；故该 0.908 **不可**与 R483 的 markdown 档 0.8125 直接相减比较。
- 存在性判定用「全仓库文件名集合」而非 inode/内容，故「误写/缺失」是路径层结论，不含内容层校验。
- R486 差分**未测**：无任何读数被生成，`verdict-r486.json` 尚未产生；不得引用其预期值当结论。
- 本轮无 C# 改动 ⇒ 无 AOT 证据；未 push（`PUSH_PAUSED` 在效）。
