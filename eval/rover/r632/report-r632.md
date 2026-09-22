# R632 · 器件面收口轮（判据族对齐 / 策略声明 / 驱动器声明刷新）＋ 文献小步

**一句话**：R631 自捕的**三处器件缺陷**（判据族 ≠ 预注册 / `unreliable_policy` 未声明 / 轮驱动器声明滞后）
在本轮**全部关闭**，并新捕三处（器具取数层假红、缺声明判绿、台账自带假断言）；**零产品源码改动 / 零真机臂 /
零远端调用 / 零新增夹具 / 零新增开关** —— 全部读数取自 **R631 冻结快照**（零重测，承 RF0005 §10
「缺派生件时重跑的是后处理，不是测量」）。**本轮不产生能力面结论**；重审结果 = R631 面 **rc=3（有效窗<2 ⇒ 停链造窗）**。

## 1. 轮形与单变量

| 项 | 值 |
|---|---|
| 轮形 | **器件/判决面收口轮**（同 R629 先例）⇒ 单变量轴**不适用**（预注册自陈，禁计为单变量轮） |
| 真机臂 | **无**。理由：三个待修项全部是判决/声明/策略面缺陷，修法不产生被测读数；引入真机臂会把「器件面是否修好」与「质量轴是否变化」混为同一读数（RF0005 §1 硬约束 6 机制面/能力面分离） |
| 数据面 | R631 冻结件（`~/.agentframework/harness/runs/r631` transcript/cases/runs.jsonl + `eval/rover/r631/evidence/windows/**`），逐件 sha256 落盘 |
| 产品源码 | **零**（`git diff --stat src/` 空）；无 build / 无 AOT |
| 跳步 | 构建/AOT（无新二进制可构建）；真机跑（零真机臂）—— 均已在预注册 `skip_steps` 写明原因 |

## 2. 判据族（D1–D5 + W）逐条读数

| 判据 | kind | 读数 | 状态 |
|---|---|---|---|
| D1 判据族对齐 | instrument（**主判据**） | 键集合逐键相等（8/8）∧ `primary_criterion_key = J1_fallback_exercised` 由机读字段绑定 ∧ 全部键带声明状态 | **pass** |
| D2 策略声明先行 | instrument | 键齐 ∧ 声明先行（`policy_declared_ts 2026-09-22T03:27:16Z`）∧ 机检三态 ∧ 缺键 fail-closed；**但对 R631 既有窗 `POLICY_ACTIVE=false`**（B2：窗 artifacts 早于声明的适用点 ⇒ 拒绝追溯套用） | **informational**（`authority = R4 manual（B2 拒绝追溯套用）`；**不得**读作机检行使） |
| D3 驱动器声明一致 | instrument | 修前 **6/6 漂移** → 修后 **0/6**（checked=6 drifted=0 absent=0）；实盘段 sha256 **逐字节不变** | **pass** |
| D4 历史判决未改写 | instrument | 四件（`verdict-r631.json` / `verdict-j4ab-r631.json` / `kpi-table-r631.json` / `prereg-r631.json`）与 HEAD blob **逐字节相等** | **pass** |
| D5 文献小步 | process | arXiv 面 **顺延 1 次（出口 429）**；第二来源 2 篇（采信 0 / 观察 1）；台账**追加**（577→608 行，numstat 31/0） | **pass** |
| W 分辨率地板 | resolution | **not_applicable**（零真机臂 ⇒ 有效窗判据不适用；禁读作 PASS 亦禁读作红） | not_applicable |

**本件自身的同源律**：`r632_family_self_check.keys_equal = true`（自有判据族键集合 == `prereg-r632.criteria` 键集合）
—— 即**修 D2 的那条判据，本轮也施加在修它自己的器具上**。

## 3. 重审读数（R631 冻结面，零重测）

| 项 | 值 |
|---|---|
| 路径模式 | `runs-dir(A)`（两条独立路径 A/B 应给出逐位相同 criteria —— 不符即 rc=2） |
| 有效窗 | **1**（`valid_windows=1`；w224 外侧 codex 自败 56/58 ⇒ 按机械策略标 unreliable 移出配对） |
| 逐判据读数 | J0 ✅ · **J1_fallback_exercised ✅（fallback_runs=6 全通过）** · J4a ❌ · J4b ✅ · J3 ❌ · J6 informational · W ❌（valid=1） · P11 ✅（前置器 rc=1） |
| 判决 | **rc=3**「判据不可判（有效窗<2）」⇒ 按 RF0005 §3：**停链先造窗**（禁下调阈值） |
| 判决来源 | 显式谓词 `verdict_source.key = J4a_capability_replication;J3_cost`（次级判据红 = rc 1 档；本轮 rc=3 由 **W 有效窗<2** 抬升 ⇒ **禁把 rc=3 读成「器件已修好」或「能力变差」**） |
| 铁律 11 | 前置器 rc=1 ⇒ R631 的质量/成本列**仍标「参考（未可验收）」**，本轮**不改写**该标注 |

## 4. 本轮新捕缺陷（三条，全部自伤/自捕，逐条入档）

1. **D4 取数层假红**：`git show HEAD:<path>` + `.strip()` 丢尾字节 ⇒ 四件 sha 必然不等 ⇒ D4 判红（rc=2）。
   判别形态 = 四条 head 侧 sha **同值异常** ⇒ 指向取数层；修法 = `git cat-file blob` + bytes 管道。
   修后 rc 2→3（**判据本身未放宽**）。
2. **缺声明判绿**：声明检查器 v1 对**无声明块**的驱动器判 PASS（把「缺声明」读成「一致」）⇒ 假绿。
   修法 = 三态 verdict（PASS / DECL_DRIFT / **DECL_ABSENT**）+ 退出码只读 verdict；四态正负控 8/8。
3. **同名判据两套谓词 ⇒ R631 行读数被证伪**：R631 kpi 行把 `J1_fallback_exercised` 读作 `NOT_EXERCISED（回退 0 行使）`；
   按 prereg-r631 的**同一键名谓词**重审冻结件得 **pass**（`fallback_runs=6`、回退跑次 `executed>0` 全部、T 面覆盖全）。
   判别形态 = 旧件族键名相近而谓词不同（`J1_exec_face_consumed` vs `J1_fallback_exercised`），
   只看键名或只看旧行自报都会沿用错读数 ⇒ **用预注册谓词在冻结件上复算**。**不改写** R631 历史行，纠偏只落本轮。
4. **台账自带假断言**：R632 台账初稿写「`prefix_tokens` 未落盘 / 无消费者」——**为假**：
   生产者 `src/agent.modelqueue/LocalSessionCacheLedger.cs:86,100,111,112`、消费者 `eval/rover/r411/verify.py:43`、
   阈值件 `eval/rover/r410/prefix-reuse.json:3`（`required_prefix_tokens 4224`）。同轮**勘误**落地。
   教训：**一次 grep 无命中 ≠ 不存在**（与「有代码行 ≠ 生效」互为反面）。

## 5. 负控（有牙证明，三步）

| 步 | 期望 | 实测 |
|---|---|---|
| STEP1 修前窗口（旧裁判件） | 判红（键族不同源 + 两机读字段缺席） | red=true（缺 5 / 多 15；`primary_criterion_key` 与 `verdict_source` 均缺席） |
| STEP2 修后窗口 | 全绿 | green=true（D1 pass ∧ 来源显式） |
| STEP3 牙证明（单变量变体） | 10/10 必转红 | 10/10 转红（逐键删除 8 + 多键 1 + 主判据键多重 1） |

- 修前读数**原样保留、不翻案**（旧裁判件判决仍不予采用）。
- 声明检查器四态：合成一致头 PASS / 字段注入 5/5 DECL_DRIFT / 空头 DECL_ABSENT ⇒ **非恒红、非恒绿、fail-closed**。

## 6. 诚实边界

- 本轮**零真机臂** ⇒ 对**质量轴**零信息量；rc=3 只说明「R631 面上的能力结论不可判、须先造窗」。
- `unreliable_policy` 对既有窗的适用受 **B2** 限制：R631 窗先于策略声明 ⇒ 严格意义上**拒绝追溯套用**；
  本件如实给出 `authority` 字段（机检行使 vs R4 人工单列），不把人工判断包装成机检。
- D4 的「轮前 pin」以 **HEAD blob** 为锚（HEAD 提交早于本轮 prereg `written_at`）；`run_r631.sh` **不在** D4 清单内
  （它是本轮声明刷新的对象），其实盘段由 D3 单独钉住（`body_unchanged=true`）。
- 文献面：arXiv 出口本轮 429 ⇒ **顺延**，不计入「连续 0 采信」（未达 3 ⇒ **不降频**）；第二来源两条均判
  「已实施 / 观察」，**无新候选**；Semantic Scholar 无 key ⇒ 引用数**不可用**（不编造）。
- **反面口径**：`required_prefix_tokens=4224` 是**本仓自标定**值，与厂商文档的 `1,024` 属不同栈口径，
  **禁直引互换**（承「禁照抄外部默认参数」）。

## 7. 复现命令（全部 `--no-build` 无关，纯脚本；本仓 cwd 可跑）

```bash
cd /home/agentuser/AgentFramework
python3 eval/rover/r632/decl_driver_check_r632.py --selftest                 # 四态正负控 8/8，rc=0
python3 eval/rover/r632/decl_driver_check_r632.py --sh eval/rover/r631/run_r631.sh --round r631   # 修后 6/6 一致
python3 eval/rover/r632/negctl_r632.py                                       # 披露式三步负控，rc=0
python3 eval/rover/r632/policy_gate_r632.py                                  # 策略三态机检
python3 eval/rover/r632/judge_align_r632.py --D ~/.agentframework/harness/runs/r631 \
        --json eval/rover/r632/verdict-r632.json                             # rc=3（有效窗<2）
python3 eval/capability/decl_sweep.py --check                                # 全表声明：checked=30 drifted=0
python3 eval/capability/status_gen.py --check                                # 收口判据：PASS
```

## 8. 下一轮

主判据 rc=3 ⇒ **先造窗**（与历史不相交的新窗集），把 `AGENTFRAMEWORK_R1_ACTION_EXEC` 之外的**承重缺口**
（`wythoff` 族 R621 记录 45/45 真值 vs 本侧缺口）作为下轮真机对照靶点；文献小步按候选队列推
（前缀长度打点的**远端侧**可达性 = 前置条件，见台账 R632 段）。
