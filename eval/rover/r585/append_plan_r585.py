import io, os, json
REPO = "/home/agentuser/AgentFramework"
p = os.path.join(REPO, "docs/reports/iteration-master-plan.md")
txt = io.open(p, encoding="utf-8").read()
assert txt.rstrip().endswith("。") or True
assert "R585" not in txt, "已存在 R585 段（幂等保护）"

block = (
    "- **R585（主线对照轮 · 器具环境恢复后首次可起臂；零产品源码改动 / 零新夹具语义 / 零新开关）**: "
    "**修改点** ① **前置件落点修复**：R584 前 harness 前置件只存 `/tmp` 且已被回收（R585 定因） ⇒ 落点改为稳定路径 "
    "`~/.agentframework/harness/runs/r585`（`restore_env_r585.py` 等价性证明 + 回读），驱动器起手自恢复、仍缺则 `exit 3` fail-closed"
    "（合「只存 /tmp 的产物入仓」先例 `1dac7689` 的同类纪律）；② 驱动器 `run_r585.sh` 派生自 `run_r571.sh`（轮号/臂集合/剂量键**三枚显式 unset**/"
    "二进制 sha 运行前后一致性断言/起手闸条款）+ 判据器 `kpi_r585.py` 派生自 `kpi_r571.py`（主线段改 C0/C1/C2，无剂量轴）；"
    "③ 台账行 `eval/capability/kpi.jsonl`（键集与同族既有行逐字相同，同轮原地更新 ⇒ 幂等）+ 报告 `eval/rover/r585/report-r585.md`。"
    "**真机读数**（3 窗 `w154..w156`，每窗 = 真值 ×1 + 产品默认档 ×3；冻结题集 sha `e0c667c2…` 与 R559–R583 同件；二进制 sha `4b70fd7c…` 运行前后一致）："
    "**质量（58 例）** 真值逐窗 `56 / 58 / 58`（中位 58、极差 2）vs 产品默认档逐窗中位 `58 / 50 / 55`（中位 55、极差 8；逐跑次 `58,58,58 / 53,50,47 / 58,48,55`）。"
    "**判据裁定 rc=1 FAIL**：C0 真值 `w154` 自身 56/58（`wythoff#55/57-hidden`）⇒ 该窗标 unreliable 不进配对（**该 2 例单列，不记我方缺陷**）；"
    "C1 有效窗 = `w155/w156`，配对差（产品−真值）= `[−8, −3]`、中位 **−5.5** < 预注册下限 −2 ⇒ **质量未达判据**（逐窗下限 −15 全过；有效窗 2 恰达下限）。"
    "C2 成本三列（**因铁律 11 rc=1 ⇒ 一律标「参考（未可验收）」**）：调用 20 vs 74（−73%）/ 新算 prompt 5,601 vs 28,392（−80%）/ completion 48,941 vs 23,907（**+105%**）/"
    "命中率 v_all 0.97 vs 0.97、v_incr 0.96 vs 0.97。**铁律 11**：`executable_and_correct=false`、`acceptable_scoped=false` ⇒ rc=1 未可验收，"
    "而 `self_report_agrees=true` ∧ `self_report_mismatch=[]`（独立物化实跑与在跑自报**逐条一致**）。"
    "**逐例归因**（`per-case-failures-r585.json`）：失败 **100% 集中 `wythoff` 单族**（`stdout_mismatch` 为主；`TimeoutExpired` 8 例仅 w155-r2；`rc=1` 2 例）⇒「一个模块缺陷带走整族」结构复现；"
    "超时**两条独立路径互证**（在跑自报 8 例 ∧ 前置器独立重跑同跑次 `rc=124`，50/56 —— 后 2 例因其自身超时未测，分母 56<58 为诚实边界）⇒ 非采集侧假红。"
    "**起手闸/判别力**：条款 = 阈值 + 观测振幅余量（R571 实测 swing 105MB）+ 连续 2 次 ⇒ `REQ=2713`（ceiling 2773）；A1/A2 真机 PASS（2768/2761MB）；"
    "**判别力成对控制 rc=0**（压制入带 ⇒ 基础门槛 PASS ∧ 条款 GATE_BLOCKED ⇒ 闸确行使）；泄漏自检 rc=0；起臂前按 pid 清本会话工具子进程（2 个 LSP 共 317MB ⇒ `MemAvailable` 1906→2890MB）。"
    "**自捕器具 2 件（均未放宽判据）**：① **闸输出读契约** —— 闸 stdout = pretty JSON **＋ 尾行 `out <path>`**，首版 `json.load(stdin)` 解析异常被吞成空串 ⇒ 起手闸读成「未过」并 `exit 2`：**fail-closed 生效、未起臂零污染**，"
    "修法 = 读 `--out` 落盘件（与 R571 同形），失败跑次留痕不翻案；② KPI 判据器残留 `R585M1/R585M3` 引用 ⇒ 汇总 `KeyError`，修后**只重跑后处理不重测**（`readings.jsonl` 未变）。"
    "**诚实边界**：① 铁律 11 rc≠0 ⇒ 调用/token 降幅**不得作验收依据**，completion +105% 单列不得被调用下降掩盖；② 质量列按预注册判 FAIL（中位 −5.5）；③ 跨窗摆动 8 例 ≈ 或 > 部分臂间差 ⇒ 单窗不作能力结论；"
    "④ `steps_executed/plan_steps_total`（轮数列）**本轮未测**（adapter 未取该字段）；⑤ 真值臂 rc 字段 null（外部 CLI 无本仓 rc 语义）；⑥ w154 不可配对 ⇒ 有效窗仅 2，不补窗。"
    "**轮志**：`eval/rover/r585/report-r585.md` · 预注册/DAG：`eval/rover/r585/{prereg-r585.json,dag-r585.md}` · 台账：`eval/capability/kpi.jsonl`（R585）。"
    "\n"
    "- **下轮候选 (R586)**: ① **`wythoff` 单族失分收口**（本轮唯一承重族：先量「同族内失败例的分布 + 是否落在同一子规格」再改，禁预防性机制轮；须产品改动放行） ② **轮数列补齐**（`steps_executed/plan_steps_total` 进 adapter ⇒ 六格报表的「步数/轮数」列由「未测」转实测） "
    "③ **`TimeoutExpired` 与 `stdout_mismatch` 分离臂**（固定 60s 截止的敏感性：同族同例复跑 3 次判「不收敛 vs 慢」） ④ 铁律 11 前置器分母补齐（本轮 `50/56` ⇒ 对超时例补独立判定） ⑤ 主线：`w154` 类「真值自身失分窗」的配对口径（单列 vs 剔除）在预注册里写成显式二选一。"
)
io.open(p, "a", encoding="utf-8").write("\n" + block + "\n")
back = io.open(p, encoding="utf-8").read()
print("R585 count", back.count("R585"), "| R586 count", back.count("R586"), "| lines", back.count(chr(10)) + 1)
