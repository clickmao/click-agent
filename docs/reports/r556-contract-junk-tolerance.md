# R556 —— 契约面「完整值 + 尾随内容」容错修复 (单变量, 同窗配对 + 外部真值同窗)

日期: 2026-09-18 (30 分钟 tick) · 驱动器 `eval/rover/r556/run_r556.sh` · 题面 `eval/rover/r556/taskset-r556.json` (g1, 58 隐藏用例)
**禁 push 生效** (`.git/PUSH_PAUSED`); 一切提交仅本地。

## 0. 从 R555 到 R556 的定因 (先量分布 ⇒ 定因 ⇒ 才修; 非预言式)

R555 §8 候选① = 上游契约面退化轴 (rc=4 stage=contract)。本轮先把它**定因**, 得到两条硬证据:

1. **transcript 报错文本本身就是"首个值已完整"的证据**:
   - `A0_84`: `'"' is invalid after a single JSON value. Expected end of data. LineNumber: 0 | BytePositionInLine: 5503.`
   - `A1_82`: `'0xEF' is invalid after a single JSON value. … BytePositionInLine: 5851.`
   该 STJ 报文只在「**先成功解析出一个完整 JSON 值**、其后还有非空白内容」时出现 ⇒ 首答的契约 JSON 本体是**完整**的, 尾部多余内容才是失败点。
2. **中继 dump 给出机制** (`/tmp/r555/adapter/side-agent-*.json`):
   - 请求侧: 出现 3 消息形态, 末条 = `[系统] 上一轮回答在输出预算处被截断了…只输出断点之后的剩余内容` (= 续写提示, 即 `LooksTruncated` 触发);
   - 响应侧: 这些续写请求的响应体是**片段** (首字节即无开头, 例 `"path":"games/__init__.py"` / `"},{` / `,第 r 堆取走后剩 a[r]-r。`)。
   ⇒ 旧判据只看**末字符**是否有 `=([{,+-*/\:` ⇒ 对"完整 JSON + 尾随散文"这类回复**假阳性**: 白发一次全价调用 (≈8.4k prompt), 再把尾随段拼回原文, 使本来可解析的首值 + 散文整体过不了严格解析 ⇒ 整窗作废 (R552 62%, R555 2/6)。
3. **KPI 口径副作用**: R555 中继 dump 19 条 vs transcript Σcalls=14 ⇒ 续写调用**从未进过本侧账**; 本轮调用/命中一律按 dump **索引区段**归属 (禁跨轮相减)。

## 1. 修复 (单变量; 契约前缀逐字节不变 prefix_chars=15291 sha=f1280f71…)

| # | 位置 (单一真源) | 变更 |
|---|---|---|
| ① | `tools/r1gen/gen_csharp.py` → 生成 `src/agent/contract/StructuredContract.cs` | 新增 `ExtractLeadingValue` (字符串感知配平扫描, 只取**开头第一个完整值**) + `TryParseOrNull` + `CanonicalJson`; `Validate`/`TryParse` 走**同一** CanonicalJson 路径。取不到完整值 ⇒ **fail-closed**, 原报错原样带出。 |
| ② | `src/agent.modelqueue/ModelQueueRouter.Recovery.cs` | `LooksTruncated`: 正文首字符为 `{`/`[` (结构化正文) 时, 截断判据改为**首个值是否配平闭合** (闭合 ⇒ 非截断; 未闭合 ⇒ 真截断, 含"断在字符串中途"这类旧判据漏判); 非结构化正文仍走原有末字符启发式。 |

生成物同源闸: `python3 tools/r1gen/gen_csharp.py --check` ⇒ `R1GEN_DRIFT_FILES=0 R1GEN_EXIT=0`。
单元证据: `dotnet test --filter "StructuredContractTests|TruncatedReplyRecovery"` ⇒ **36/36 通过**, 含
正控 (完整契约 + 尾随内容 ⇒ 0 错误; 两个值 ⇒ 取首值) 与负控 (真截断 ⇒ 仍拒; 纯散文 ⇒ 拒)。
AOT: `dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64` ⇒ **IL 警告 0**;
`/tmp/pub_r556/agenthost/agenthost` sha256 `320d0eb17e709d15ce7d149ceff45fc1cacff814ac01b9fbda67f702726cee48` (15820208 B)。
未修复对照件 = R555 交付件 `/tmp/pub_r555/agenthost` sha256 `d28132182f43aa9e866824924865499086ca7ac9a9d35128dad5692488025f08` (15816112 B) —— 逐位校验在 runner 第 0 步落盘 (`eval/rover/r556/bins-r556.json`)。

## 2. 本轮读数 (4 窗 × 3 臂, 同一 adapter 会话; 每窗 = [codex C1] → [A0 未修复] → [A1 修复件])

| 臂 | 质量(逐窗/中位/极差) | 调用 | 新算prompt | completion | 命中率 (v_all·v_incr, 中继 dump) | rc |
|---|---|---|---|---|---|---|
| C1 (codex 外部真值, 同窗) | 58/58/58/58 · 58 · 0 | 28 | 15190 | 12333 | 0.9373 · 0.9591 | 0 |
| R556A0 (未修复) | 47/58/**0**/56 · 51.5 · 58 | 8 | 1919 | 19106 | 0.9716 · 0.9614 | 5/0/**4**/8 |
| R556A1 (修复件) | 58/51/58/58 · 58 · 7 | 7 | 1948 | 16448 | 0.9671 · 0.9479 | 5/5/0/0 |

**主判据 (C4) 同窗配对**: w92 内 A0 死在契约面 (`rc=4 stage=contract`, 0/58) 而 A1 同窗同题面同夹具 **58/58 `rc=0 stage=done` (1 次调用 / 新算 151 B)**;
契约面死亡率 A0 **1/4** → A1 **0/4** (R555 异轮参照: 2/6)。**修复生效, 且无回退** (A1 中位 58 ≥ A0 中位 51.5; 调用 7 ≤ 8)。

**成本 (C1)**: 新算 prompt 1948 vs codex 同窗 15190 ⇒ **−87.2%**; 调用 7 vs 28 ⇒ **−75%**; 逐窗四项均 ≥30% 降幅 (488/4258, 496/3678, 151/3984, 813/3270)。
**质量 (C2)**: A1 中位 58 = codex 中位 58 (判据: 中位差 ≥ −2); 但 w91 的 51/58 = 已知 `wythoff` 模块退化窗 (R555 亦 51/58, 失分点 `wythoff#43-public,44,45,47,48,49,50`), **未闭合**。

## 3. 铁律 11 前置器 (独立执行路径)

`python3 eval/rover/r507pre/exec_precondition.py --round r556 --out /tmp/r556/precond-r556.json` ⇒ **rc=1** (逐条点名 w90/R556A0 47/58, w91/R556A1 51/58, w92/R556A0 0/58, w93/R556A0 56/58; `SELF_REPORT_AGREES=True`; `SCOPE_SOURCE=prereg-r556.json PREREG=True`)。
⇒ 依令: 本轮 **成本读数标「参考 (未可验收)」, 禁作验收依据**。修复件自身 3/4 窗 58/58 且 `correct=True` 由独立路径复核。

## 4. 诚实边界

- 4 窗样本对"契约面死亡率"仍小 (修复前观测 33%~62%); 本轮 1/4 (A0) 只是**同窗配对证成**所需的那一次命中, 不作分布估计。
- 起手闸 A 首测 `GATE_BLOCKED (mem=2519MB, gate=2650MB)`: 释放两个 Hermes LSP 子进程 (bash-language-server 129MB + pyright 212MB, 会按需重启) 后 PASS (2774MB); 与 improvements.md 已登记的「A1 闸缺自身工具子进程自排除 ⇒ 假阳性」**同一缺陷**, 仍未闭合 (未改器具, 本轮以释放内存绕过)。
- 与 R555 的 2/6 只作**异轮分布对照**, 不作相减。
- `R556A0`/`C1` 臂的正确性不是本轮判据 (对照组), 但仍在 prereg `evidence_scope.require` 内 (不挑选面) ⇒ 前置器 rc=1 由此与 w91 的 wythoff 窗共同构成。

## 5. 下轮候选

① `wythoff` 模块退化窗 (最高优先; 只翻既有开关, 禁新增夹具): 本轮 A0/A1 各出 1 窗, 与 R554/R555 同源, 是质量面的唯一失分集中区。
② 契约面死亡率再加样本 (≥8 窗) 以把"0/4"升级为分布读数; 且把 `ContractSalvage` 是否触发**可见化** (现为零副作用静默容错, 仅在 dump 侧可回溯)。
③ 起手闸 A 自排除闭合 (先写后跑): 把自身工具子进程 (LSP/kernel) 纳入排除面 ⇒ 消掉 2500/2650MB 的假阳性。
④ 调用账口径收口: `transcript.calls` 与中继 dump 的差额 (续写调用) 应在 transcript 侧显式记账, 否则每轮都要靠 dump 反推。
