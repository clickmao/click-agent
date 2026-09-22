# R631 · 执行面轴跨窗复现轮（w223/w224）+ 器件面两处自捕缺陷

**一句话**：把 R621 已证的 `AGENTFRAMEWORK_R1_ACTION_EXEC` 质量效应（+33pt）放到**与历史窗集不相交**的新窗集
（w223/w224，reps=3/窗）上重测 ⇒ **未复现**（逐窗配对 Δ 中位 **0**、符号翻转 ±0.3333）；外部真值臂在 w224
自身失分（codex 56/58 ⇒ 该窗 unreliable）；铁律 11 前置器 **rc=1**（验收面 3 跑次未全对 + 判据器 2 条假红，已修）
⇒ **本轮一切读数标「参考（未可验收）」**。

## 1. 单变量与臂表（唯一自由度 = 窗集）

| 项 | 值 |
|---|---|
| 轴 | `AGENTFRAMEWORK_R1_ACTION_EXEC`（T `=1` ⇒ 执行面 = 采纳候选映射；C `unset` = 产品缺省 off） |
| held-constant | `AGENTFRAMEWORK_R1_ACTION_PROMPT=legacy`（两臂同值；legacy 前缀锚 chars 15675 / sha a9792fdbe5b2…） |
| 被测件 | `$HOME/.agentframework/artifacts/pub_r630/agenthost`（**零产品源码改动**，无 build/AOT；全臂同一枚件） |
| 窗集 | w223、w224（历史用至 w222 ⇒ 不相交）；题集 = r610 冻结件逐字节复制（sha e0c667c2…） |
| 与 R621 的差异 | **仅窗集**（w217..w219 → w223..w224）与 reps（6 → 3/臂/窗）；同轴同档位同 held-constant ⇒ 只并列、禁相减 |

## 2. 读数（冻产后处理复算：`eval/rover/r631/recompute_j4ab_r631.py`）

| 窗 | T 整题全对 | C 整题全对 | codex 真值 | Δ(T−C) 全对率 | Δ(T−C) 用例中位 | D(产品−真值) 用例中位 |
|---|---|---|---|---|---|---|
| w223 | 2/3 | 3/3 | 1/1（58/58） | −0.3333 | 0 | 0 |
| w224 | 1/3 | 0/3 | 0/1（**56/58, 真值未全对**） | +0.3333 | +1 | −5（**reliable 剔除**） |

- **J4a（复现判据）不通过**：Δ 中位 = 0.0（判据要求 > 0 且逐窗符号非负占比 ≥ 1/2，实测 0.5 恰好擦线但中位不满足）
  ⇒ 按 RF0005 §3 R2/R5，`AGENTFRAMEWORK_R1_ACTION_EXEC` 在**本轮窗集上判「非承重变量」，定案关闭**，
  禁再为同一缺口加轮、禁宣称增益。n=2 窗**欠功率**，只作趋势不作能力结论。
- **J4b（对外部真值）通过（唯一可靠窗）**：w223 D = 0（持平）；w224 因真值自败（56/58）按 R4 标 unreliable 不并入。
- **成本三列（中继 dump 时间轴，非 transcript.calls）**：T 1.83 调用 / 1,555 新算 prompt / 4,491 completion；
  C 1.83 / 1,513 / 4,434；codex 5.5 / 4,195 / 3,872。两产品臂**成本相等** ⇒ 该轴**既非质量杠杆也非成本杠杆**。
  与 codex 的对比属**跨实现方向读数**，因 rc=1 一律标「参考（未可验收）」。
- **rc 分层 v4 的真机实践**：14 跑次中 9 条 `rc≠0`（5 = `expect_stdout_exhausted`、8 = `self_test_unmet`），
  其中 **6 条产物仍 58/58** ⇒ 采用「rc≠0 可能只是**来源命名**、结果行才是结果」的读法后，这些跑次被判为**结果**
  而不是 VOID（此前口径下会被整轮作废）。**非零 rc ≠ void** 的判据在本轮首次有真机数据背书。

## 3. 命名阻塞（铁律 11 验收面，rc=1）

`python3 eval/rover/r507pre/exec_precondition.py --round r631` ⇒ `VERDICT_BLOCKED` / `rc=1`：

| 阻塞项 | 内容 |
|---|---|
| w223/agentT-r1 | 54/58（wythoff#45/#47/#48/#49-hidden） |
| w224/agentT-r1 | 51/58（7 条 wythoff） |
| w224/agentT-r3 | 46/58（12 条 wythoff） |
| 非验收面单列 | agentC 4 跑次（58/58、56/58、44/58、50/58）+ codex w224 56/58 ⇒ 全局 blocked 9 项 |

⇒ 验收面（预注册 `require` = 治疗臂 w223/agentT-r* 与 w224/agentT-r*）存在未正确臂 ⇒ **未可验收**；
本轮 token/调用类降幅一律标「参考（未可验收）」，禁作验收依据。

## 4. 器件面（本轮自捕缺陷，均留痕不翻案）

| # | 缺陷 | 证据 | 处置 |
|---|---|---|---|
| D1 | 前置器**通配声明存在性检查不同源**：分类用 `fnmatch`（`_scope_of`）而缺席检查用字面 `isdir(snap/win/<模式>)` ⇒ 通配声明恒判缺席（r631 声明 `w223/agentT-r*` 而 `agentT-r1..r3` 三目录俱在，仍报 `DECLARED_ARM_ABSENT`）×2 条；历史同类 r550 ×3 条 | 修前 `DECLARED_ABSENT=w223/agentT-r*,w224/agentT-r*`；`ls snapshots/w223` 三目录在盘 | **已修**（同源改用 fnmatch 对已落盘目录匹配，零匹配仍 fail-closed 报缺席）；两控: ① 正控修后 `DECLARED_ABSENT=-` 且 rc 不变 1；② 负控注入字面缺席名 `w223/agentT-r9` ⇒ 仍报缺席（牙在，且新增 `VERDICT_POSTHOC_ONLY` 事后声明不当验收面）；③ 历史判决审计 r550 重放: `declared_absent` 3→3、rc 不变 ⇒ **判决中性**（r550 的 3 条为**字面**名 `agentR550on2-g1`，与本修无关） |
| D2 | `judge_r631.py` **判据族与预注册不同源**（旧草稿残留）：其 `kind` 写「第五次刀 = 等价面分辨率取证 reps 3→6 / 窗集 w217..w219」，输出判据键为 `J6`/`v3`（`NO_RESOLUTION`），而预注册声明 `J0/J1/J4a/J4b` | `verdict-r631.json:instrument_source` 与 `prereg-r631.json:criteria` 并列比对 | **该件判决不予采用**（保留在盘、不删、不翻案）；本轮判决改用**冻产后处理复算**（§2 脚本，幂等、零重测）。R632 义务: 判决件判据族与预注册对齐（判据器改版**禁跨轮相减**） |
| D3 | `run_r631.sh` 头部注释**声明滞后**（写 w211..w213 / 端口 49793 / `PREV_SWING` 125MB），实盘为 w223..w224 / 49795 / `REQ=2769`（prev_swing 119） | 起手闸日志 `ceiling=2854 prev_swing=119 margin=119 REQ=2769` vs 头部 ⑦ | 已在本轮**记录**（文件未改: 运行期禁编辑在飞器具）；R632 派生该脚本时按实盘值刷头部 |

**另记**：本轮**未**声明 `unreliable_policy`（前置器 `POLICY_ACTIVE=False reason=no_policy_key`）⇒ 真值自败窗
（w224）**未被机检降级**，其失分留在验收面读数里。R529 J4(b) 的正确用法 = **起臂前**声明该键 + `policy_declared_ts`
（前置器用 mtime 判「先声明再跑」）⇒ 列入 R632 起手清单。

## 5. 复现命令

```bash
set -a; . ~/.agentframework/keys.env; set +a
export DOTNET_ROOT="$HOME/.dotnet"; export PATH="$DOTNET_ROOT:$PATH"
bash eval/rover/r631/run_r631.sh                       # 起手闸 A1/A2 + 前提闸 + 14 跑次
python3 eval/rover/r631/recompute_j4ab_r631.py         # 冻产后处理复算（J4a/J4b）
python3 eval/rover/r507pre/exec_precondition.py --round r631   # 铁律 11 验收面（rc=1）
```

## 6. 诚实边界

- n=2 窗、reps=3 ⇒ 欠功率：**「未复现」不等于「效应不存在」**，只等于「在本窗集上不足以支持该轴承重」。
- 真值臂 w224 56/58：真值自败**不等于**夹具缺陷（按 skill: 真值自身失败的例必须单列，不得记为我方能力缺陷），
  但该窗的对照列确实不可用。
- 与 codex 的成本对比为跨实现方向读数（且 rc=1）⇒ 不作收益宣称。
- R630 的 `spec` 轴与 R612–R630 的质量轴读数**跨轮禁相减**，本轮只作并列观测。
