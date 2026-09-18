# R562 · 器具收口轮：判据 v2 入册 + 起手闸/判据器/铁律11 联合回归 + wythoff 族只读定因

- **日期**：2026-09-18 ｜ **轮号**：R562 ｜ **HEAD 起点**：`2894fe0`(R561)
- **单变量**：无（**零新臂 / 零产品源码改动 / 零远端调用 / 零新增夹具与开关**）⇒ 本轮**不宣称任何质量或成本降幅**，一切读数标「参考（未可验收）」。
- **铁律 11**：`exec_precondition --round r559` ⇒ **rc=1**（blocked 5）· `--round r560` ⇒ **rc=1**（blocked 12）——同一前置器/同一冻结快照的**复跑**读数（非本轮新交付）。

## 1. 修改点（本轮产出物）

| # | 修改点 | 落点 |
|---|---|---|
| ① | **质量判据 v2 入册**（v1 声明作废 + 作废登记，不改写历史轮志） | `docs/external-reference-harness.md` §12 / §12.1 / §12.2 |
| ② | 判据 v2 **复跑一致性**（零新臂，判决面逐字段比对） | `eval/rover/r562/verdict-r562-rerun.json` |
| ③ | 起手闸**成对控制联合回归**（mem 面 + shell 自匹配面 + 多因并列；诱饵前提经 `/proc` 核实） | `eval/rover/r562/gate_regression_r562.py` + `gate-*.json` + `gate-regression-r562.json` |
| ④ | wythoff 族**只读定因**（405 例次重放冻结副本；独立 oracle 复现 15/15 期望值） | `eval/rover/r562/wythoff_cause_r562.py` + `wythoff-cause-r562.json` |
| ⑤ | 收口聚合 + 台账行（键集与同族既有行逐字相同；缺陷态行原样留档） | `eval/rover/r562/collect_r562.py` + `verdict-r562.json` + `superseded-kpi-line-r562.json` + `eval/capability/kpi.jsonl` 末行 |

## 2. 读数（真机/离线，均为已落盘件的机检结论）

| 面 | 判据 | 读数 | 结论 |
|---|---|---|---|
| A 判据 v2 复跑 | 判决面 6 字段 vs 已提交 `verdict-r561.json` | 逐字段相同；影子自检 6/6 | **一致** |
| B 逐例矩阵 | `percase-matrix-r561.json` vs r559/r560 `report.json` 的 `cases_pass` | **27/27** 臂窗相等 | **一致** |
| C 双路径交叉 | 定因器失败例集合 vs 铁律 11 前置器 `blocked` 串 | **27/27** 臂窗逐条相同 | **一致** |
| D 起手闸回归 | 5 档成对控制期望 rc/verdict | `0 PASS / 2 GATE_BLOCKED / 0 PASS / 2 GATE_BLOCKED / 2 GATE_BLOCKED`，`expectations_violated=[]` | **rc=0** |
| E 夹具-题面 | 独立 oracle 复现 15 条 wythoff 期望值 + 判据器自检 | 15/15 正控；59 变异 0 误放行；phi 集 == 暴力递推集 | **夹具缺陷分支排除** |
| F 定因分布 | 405 例次未逐字节匹配的语义分类 | `MOVE_NOT_COLD 67 / LOSE_FOR_WIN 34 / WIN_FOR_LOSE 19 / MOVE_ILLEGAL 6 / LOSE_LABEL_MISMATCH 4 / MOVE_NOT_LEXMIN 1` | 主因 = **胜负判对、落点非冷点**（51%） |
| 形式校验 | `VerificationForm|SkillGeneralization|DevPlanDocRef` | 14/14（Failed 0 / Skipped 0，`FORMCHECK_EXIT=0`） | **绿** |

**wythoff 逐窗通过数（/15，w104→w112）**：真值 `15/15/15/13/4/15/15/15/9`（w108=4 ⇒ **真值崩窗**）｜R559B0 `0/2/3`｜R559B3 `13/15/13`｜R560B0 `13/15/2/7/12/10`｜R560B3 `7/4/15/0/15/12`。
**摆动**：真值 15/15 例、R560B0 13/15 例、R560B3 15/15 例在窗间既过又败；同例**同输入不同输出**例数 15/13/15 ⇒「残余固定几例」推断**被否证**（R561 结论在机制层得到复核）。

## 3. 候选台账（用户令：全部候选并入本轮；未做的必须写明原因）

| 候选 | 状态 | 结果 / 未做原因 |
|---|---|---|
| ① wythoff 族按族定因 | **做**（只读） | 405 例次重放 + 独立 oracle ⇒ 主因份额与逐窗摆动读数落盘；**修复须动契约/产品分支 ⇒ 待放行** |
| ② 交付闸 / 停止条件（rc=8/rc=5 仍交付） | **未做** | 需新增产品分支 ⇒ **待放行**（本轮零产品改动） |
| ③ 判据 v2 收口到台账（v1 作废） | **做** | `docs/external-reference-harness.md` §12（含作废登记） |
| ④ 起手闸/共享机测量口径与判据 v2 联合回归 | **做** | 判据面 27/27 + 27/27 + 6/6；起手闸 rc=0（5 档控制） |
| 遗留：契约面死亡样本扩样 | **未做** | 需新窗（新臂）⇒ 与「零新臂」冲突，且用户令「不许新增夹具与额外开发」 |
| 遗留：`transcript` 缺 `max_exec_repair` 字段 | **未做** | 属产品侧遥测字段 ⇒ 待放行 |

## 4. 本轮自捕（器具缺陷，全部 fail-closed 挡住、未污染真读数；缺陷态读数原样留档不撤）

1. **定因器冷点集漏 `(0,0)`** ⇒ 终端招法（`WIN 1 1` → `(0,0)`）被误判 `MOVE_NOT_COLD`，且**逐字节判分被语义类替代**（首版未独立记 `match`）⇒ 修：`(0,0)` 入集 + 主判据改为逐字节（语义类只作定因）。
2. **双实现交叉校验的域/排序不一致**（phi 序 vs 暴力递推的排序与状态空间）⇒ 首跑 `phi_vs_brute_equal=false`，fail-closed 拦下（rc=2），修后相等。
3. **LOSE 词标不符被并入 `OK`**（`1 2` / `3 5` / `4 7` / `6 10` 直吐冷点坐标）⇒ 单列 `LOSE_LABEL_MISMATCH`（4 例，全部在 w104/R559B0）。
4. **收官器命名错位**：「定因器按族内序编号（0..14）vs 前置器按题集全局序（43..57）」⇒ 首跑 C=10/27（rc=2 INSTRUMENT_DEFECT）；修法 = 机取映射（禁手抄），修后 27/27。缺陷态台账行留档 `superseded-kpi-line-r562.json`。
5. **诱饵前提静默落空**：`bash -c 'sleep 200' <字面量>` 会被 bash exec 替换 ⇒ `-c` 串与 `$0` 字面量消失，控制不成立（表现为 `shells_skipped_n=0`）；改为不 exec 替换的复合命令 + `/proc/<pid>/cmdline` 核实前提。

## 5. 诚实边界

- 零新臂 ⇒ **无任何降幅/增益宣称**；质量读数沿用 R559/R560 冻结件，**与旧窗并列不相减**。
- 铁律 11 rc=1 ⇒ 一切读数标「参考（未可验收）」；未达标轮不产出可验收结论。
- 定因结论**仅在 wythoff（15 例）成立**；族内摆动 > 臂间效应，禁据单窗下能力结论。
- `MOVE_ILLEGAL` 6 例**全在外部真值臂**（把「双堆不等量移除」当合法招法，题面明禁）⇒ 真值侧读题不严，不是夹具缺陷（夹具已被独立 oracle 复核）。
- 起手闸本轮 PC `mem 2652` 对门槛 `2650`（余量 2 MB）⇒ **擦边 PASS 不算窗口**（阈值 + 观测振幅余量 + 连续 2 次 + 对侧无重进程）。

## 6. 复现

```bash
export DOTNET_ROOT="$HOME/.dotnet"; export PATH="$DOTNET_ROOT:$PATH"
python3 eval/rover/r562/wythoff_cause_r562.py                        # 405 例次只读定因
python3 eval/rover/r562/gate_regression_r562.py                      # 起手闸 5 档成对控制
python3 eval/rover/r507pre/exec_precondition.py --round r559 --out /tmp/p559.json
python3 eval/rover/r507pre/exec_precondition.py --round r560 --out /tmp/p560.json
python3 eval/rover/r561/verdict_r561.py --matrix eval/rover/r561/percase-matrix-r561.json --out /tmp/v562.json
python3 eval/rover/r562/collect_r562.py                              # 收口机检 + 台账行
```
