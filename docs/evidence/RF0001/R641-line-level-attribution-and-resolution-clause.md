# R641 · R640 遗留「J4 未定因 4/5」**行级定因闭合** ＋ 判据面**分辨率条款**登记 —— 证据文档

- **轮次**: R641（2026-09-23）· 前态锚 = R640（承重缺口族只读逐例定因）
- **轮形**: **零产品源码改动 / 零重测 / 零新臂 / 零远端 / 零新增夹具语义** —— 只读复算 + 器具面收口
- **被测件**: 无（未重新构建、未重新发布；不含任何新二进制）
- **冻结面**: `eval/rover/r639/snapshots/<win>/<arm>/g1`（w237/w238/w239 × {agentP-r1..r3, codex} = **12 跑次**，只读副本上执行、零写入原树）
- **题集**: `eval/rover/r639/cases/cases-r521.json` sha256 `270128eb85c7afc07244c10c8845a22a541a7a60587a870125089e93422fccd7`（与 r610/r639 **逐字节一致**）
- **真值参照**: `eval/rover/r622/wythoff_oracle.py`（26×26 表；独立实现，与判据器/生成器零共享代码）
- **预注册**: `eval/rover/r641/prereg-r641.json`（`written_before_run: false` / `declared_before_any_reading: true`，**如实标注不包装**：v2 进程先起、落盘时 `out/` 仅存 v1 的 traceback 日志、盘上读数 **0** 件；J4b 联合臂另有 `addendum_J4b`，**先于该臂起臂落盘**）
- **DAG**: `eval/rover/r641/dag-r641.md`（起手先出）
- **判决件**: `eval/rover/r641/out/attrib-r641.json`（J0–J5/J8/J9）＋ `out/joint-r641.json`（J4b）
- **器具**: `eval/rover/r641/attrib_r641.py` sha256 `1155ea55e8e4a41d…`（与判决件内登记值一致）· `eval/rover/r641/joint_r641.py`

## 可复现采集命令

```bash
cd /home/agentuser/AgentFramework
# ① 主归因（J0/J1/J2/J3/J4/J5/J8/J9；冻结快照副本上执行，零写入；分块增量落盘 + 断点续跑缓存）
PYTHONDONTWRITEBYTECODE=1 python3 eval/rover/r641/attrib_r641.py
# ② J4b 联合最小修复臂（w239 两跑次；单行臂记录保留在 ①）
PYTHONDONTWRITEBYTECODE=1 python3 eval/rover/r641/joint_r641.py
# ③ 收口机检
python3 eval/capability/status_gen.py --check && python3 eval/capability/decl_sweep.py --check
```

## 判决读数（预注册照原样判，无放宽）

| 判据 | 读数 | 判定 |
|---|---|---|
| J0 oracle 正控 / 变异负控 | 正控 **15/15** ∧ 变异 **13/15 判红**（有牙） | PASS |
| J1 重放 ↔ **机取期望表**（两源）交叉校验 | `mismatch = 0`（主源 = R639 判决件族级分类器；次源 = R640 `per_run_wythoff`；两源不符 ⇒ rc=2 fail-closed） | PASS |
| J2 守恒式 | `Σ分类 = 12 × 58 = 696`（逐跑次 58）**恰好一次** | PASS |
| J3 **帧感知**逐例分类 | 新增类 `FRAME_TRANSPOSE` 非零：`w238/agentP-r3` **3/3**、`w239/agentP-r2` 1 ⇒ R640 判据器把这批误标为 `nonwinning_move` | PASS（暴露上位器具缺陷） |
| J4 行级最小修复（**单行**） | **3/5 CONFIRMED**（`w237/r3` 12→15 · `w238/r3` 12→15 · `w239/codex` 13→15）；2 跑次单行 `NO_EFFECT`/`PARTIAL` | 部分（非缺陷） |
| **J4b 联合最小修复（合成缺陷）** | **2/2 CONFIRMED**（`w239/r1` **4→15** · `w239/r2` **3→15**，其余三族逐例不变） | PASS |
| **J4 合计（R640 遗留缺口）** | **未定因 4/5 ⇒ 0/5**（3 单行 + 2 联合 = 5/5，`anchor_miss = 0`） | **闭合** |
| 空重写负控（每跑次） | **7/7** 与 base 逐位相同 ∧ 目标族仍 < 15 ⇒ 非「凡改即绿」 | PASS |
| J5 **判据面分辨率条款** | 采样面 **15/15** 全绿 ∧ 规格面（25×25=625 格）**610/625 判红** ∧ 反向控制（去掉 1 个采样位置）⇒ 采样面 **14/15 转红** | PASS |
| J8 确定性 | 12 跑次重放**逐位相同** | PASS |
| J9 非平凡性 | 跨跑次读数签名 **7 个互异** / 12 跑次 | PASS |

## 行级定因结果（5/5）

| 跑次 | 缺陷类 | 定位（行级） | 最小修复 | 目标族 | 其余三族 |
|---|---|---|---|---|---|
| `w237/agentP-r3` | 冷集索引 | `idx = int((b-a)/PHI)` ⇒ 索引应为**配对序号 b−a** | 单行 | 12 → **15** | 14/14/15 不变 |
| `w238/agentP-r3` | **表示面（帧）** | `solve` 内排序两堆后**未换回输入帧** ⇒ 着法按排序帧输出 | 单行 | 12 → **15** | 14/14/15 不变 |
| `w239/codex`（真值臂） | 着法合法性 | 着法枚举**未过滤非法着法** | 单行 | 13 → **15** | 14/14/15 不变 |
| `w239/agentP-r1` | **合成缺陷（2 处）** | `lower_wythoff`：① 搜索区间 `lo,hi=n,2n+1` ⇒ 循环零次 ② 返回缺 `+n` 分量 | 联合 2 行 | 4 → **15** | 14/14/15 不变 |
| `w239/agentP-r2` | **合成缺陷（2 处）** | DP：① `(0,0)` 未入必败集 ② 着法选择判候选自身而非**落点** | 联合 2 行 | 3 → **15** | 14/14/15 不变 |

> **单行实验为何对后两跑次 NO_EFFECT/PARTIAL**：合成缺陷的定义即「单行不足」——`r1` 单行 4→0 / 4→3（方向反），`r2` 单行 3→4 / 3→10（只解释 7/12）。联合臂为此类缺陷的正确实验形态，**并在起臂前声明**（`addendum_J4b`）。

## 自捕器具缺陷（**先修器具再加读数**，未放宽任何断言）

| # | 缺陷 | 类 | 处置 |
|---|---|---|---|
| E1 | J5 mutant **自身抛 TypeError**（`'WIN %d %d' % best` 且 `best=None`）⇒ 探针自崩，把判据面读数掩盖成器具崩溃 | 器具层（缺陷信息构造自身不得抛异常） | 改**见证式非 crash 构造**（采样面专用解），构造上不可能抛异常 |
| E2 | v1 只在末尾一次写结果 ⇒ 晚段崩溃**丢掉已跑完的 J4 读数** | 器具层（长跑须分块增量落盘） | 分块增量落盘（4 个 save 点）＋ replay/J4 断点续跑缓存（按 cases sha 键控） |
| E3 | J9 把 `sorted(dict.items())` 直接 join ⇒ tuple 拼串 TypeError | 器具层（trivial） | 显式 `"%s=%s"` 格式化；**不重跑失效块**（缓存复用） |
| E4 | v1 分辨率条款的 mutant 设计**结构上不可能在 25×25 规格面触发**（冷区 `a≥21 ∧ b≥21` 不含任何在格必败位） | 器具层（判据可触发面为 0 ⇒ 空心） | 改为见证式构造（采样面专用解）——**在任何读数产生之前**修正并声明 |

> v1 三处缺陷**未产生任何读数**（`out/` 从未出现结果文件）⇒ 无旧判定需翻案；v2 独立重跑，`supersedes` 块如实记录。

## 诚实边界

- 只读复算面 **≠** 真机新跑 ⇒ 读数只对 R639 冻结面成立，**不宣称生产已修**。
- 行级定因来自**副本上的最小修复实验** ⇒ 只证「缺陷在被改那一行/那两行」；`w239` 两跑次的联合臂是**合取证据**，不排除同文件内其他行亦参与。
- **无单变量轴 / 无新窗集 / 无新跑次 ⇒ 跨轮禁相减**（不与 R639 `D=[−3,0,−9]`、也不与 R640 任何读数相减）。
- **本轮无任何降幅/质量宣称**；三档终局目标读数（32 ms 级 / 快 50× / −95% / 成本 −85~91%）不动不宣称。
- 起手闸 **P3 内存读数 FAIL**（`MemAvailable` 2550 MB @3000MB 闸 / 2605 MB @2900MB 闸；机器总 3659 MB，R639 台账 REQ≈2727 MB）——本轮为**只读轮**（无 build / 无 AOT / 无真机臂）⇒ 该闸保护的资源竞争对象**未被触发**，故未阻断；读数如实入档，**未调闸值**。
- 跳步「构建/AOT」（零 `src/` 改动 ⇒ 无新二进制）与「铁律 11 前置器」（无真机臂、无降幅/质量宣称 ⇒ 无「可验收对比数据」可验），**显式声明非跳步掩盖**。

## 收口机检读数

- **形式门禁 14/14** —— `env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR dotnet test src/agent.tests/agentframework.tests.csproj --filter "FullyQualifiedName~VerificationForm|FullyQualifiedName~SkillGeneralization|FullyQualifiedName~DevPlanDocRef" --nologo -v q` ⇒ `Failed: 0, Passed: 14, Skipped: 0`（测试工程编译 **0 error**；**产品二进制跳步** —— 零产品源码改动 ⇒ 无被测件可构建）。首轮该门禁 **13/14**（红项 = `VerificationFormTests.Registry_Exists_And_HasNoViolations`，**R2c**：covers 登记了 2 条非路径叙述）⇒ 修法 = covers 只放**存在路径**、叙述移入 `note`，并在登记脚本内加 covers 存在性**前置机检**（不通过则不写盘）；修后 **14/14**，**未放宽任何断言**。
- **`status_gen.py --check` PASS**（违规 **0** / 基准漂移 **0** / 缺源 **0**）；派生件已重跑对齐现盘。
- **`decl_sweep.py --check` `DECL_SWEEP=OK`**（checked=30 / drifted=**0**；`SER_ASSERT=OK`；只读，一个字节都没动）。
- **判据面通过率**：J0 正控 15/15 · J1 mismatch 0 · J2 696/696 · J4 5/5 · J4b 2/2 · J5 15/15（规格面 610/625）· J8 12/12 · J9 7/12 互异。
- **预注册时序（如实标注）**：`written_before_run = false` / `declared_before_any_reading = true`（落盘时 `out/` 仅存 v1 traceback 日志、**盘上读数 0 件**）；J4b 联合臂 `addendum` **先于该臂起臂**落盘。
