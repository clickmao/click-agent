## 附录 S —— EXP1-Q18：落盘白名单落地修法 + 独立重放性证明（承附录 R §R.3 归因①）

> 轮次 `EXP1-Q18`（60m 自检作业，**不占主线轮号**；对侧并行执行体正在推进 R462 ⇒ 本轮**零 dotnet**）
> 证据目录：`eval/capability/exp1-q18/{prereg_q18.json,build_q18_probe.py,build_q18.json,probe_v270.py,drive_q18.py,drive_q18.json,finalize_q18.py,verdict_q18.json,evidence_q18.txt,verdict_q18_replay.json,verdict_q18_replay_old.json,verdict_q18_provenance.json,verdict_q18_provenance_old.json,baseline_shas_before.txt,VOID_FIRST_ATTEMPT.md,frozen/arm_v260,frozen/arm_v270}`
> 双臂自洽器具链：`eval/capability/q18a-v260/`（v2.6.0 对照）、`eval/capability/q18a-v270/`（v2.7.0 治疗）
> 登记行：`eval/capability/kpi.jsonl`（`EXP1-Q18`）
> 器具：`probe_v270.py` = `probe_v260.py` v2.6.0 **单变量两行**派生（`PROBE_VERSION` 常量 + `citations.jsonl` 落盘白名单）；判据器具 `unit_axis_guard.py v1.3`、`archive_field_provenance.py` **零改动**

### S.1 本轮只推进一步

落地附录 R §R.3 归因①的修法：把 `symbol_faces` / `relocated_symbol_faces` 补进探针落盘白名单，并**证明**两枚字段进入归档后，`n_symbol_faces` / `symbol_face_rungs` 两个登记读数可由归档**独立复算**（附录 Q 口径：不可重放 4 → 2）。**不在同一轮做别的候选。**

### S.2 方法（先预注册，后测量；双臂同语料单变量）

1. **单变量派生**：`build_q18_probe.py` 由产物自身派生锚点做**原位插入**（不手打长字面量 —— 承「写入通道会改写手打字面量」纪律），读回核对：逐行 diff **恰 2 行**（第 67 行版本常量、第 1590 行白名单），`probe_v260.py` sha256 `e90c7d7f…` 与 Q10 登记值逐位相同。
2. **语料冻结**：`/tmp/q18_corpus` = 工作树 rsync 快照（排除 `.git/bin/obj` 与 `eval/capability/exp1-q18/`），指纹 `bcde4dfc…`（718 个 md/cs 文件、997 条归档行）；两臂跑完复算指纹**未变**。
3. **双臂自洽链**：`probe → kind_table → unit_axis_guard`，臂目录置于 `eval/capability/q18a-<臂>/`（同深度，辅件内 `REPO = HERE.parent³` 成立）。两臂**只有器具版本一个变量**。
4. **负控成对**：对照臂 = 旧器具 + 同语料；判据器具零改动 ⇒ 差异只能归因到那一行白名单。

### S.3 读数表

| 量 | v2.6.0 对照 | v2.7.0 治疗 |
|---|---|---|
| 归档键并集 A | 24 | **25**（新增恰 `symbol_faces`） |
| 落盘白名单 D | 26 | **28** |
| `symbol_faces` 行（键在场 / 非空） | 0 / 0 | **887 / 488**（共 997 行） |
| `relocated_symbol_faces` 行 | 0 | **0**（分支未命中） |
| `n_symbol_faces` 重放 | `0`（边界，无从比较） | **622 = 登记 622，逐位相等** |
| `symbol_face_rungs` 重放 | 边界（`ARCHIVE_FACE_FIELD_ABSENT`） | **六桶全等** |
| 不可重放键 | 4 = {`n_symbol_faces`, `symbol_face_rungs`, `stale_like_n`, `symbol_occurrences`} | **2 = {`stale_like_n`(SELF_REFERENTIAL_CROSS_ARTIFACT), `symbol_occurrences`(PARAM_SCOPE)}** |
| C1 重放保真 | 12 检查 / 10 相等 / 2 边界 | **12 检查 / 12 相等 / 0 边界** |
| 归因分类 Σ=35 | archived 24 / omission 9 / branch_unhit 2 | **archived 25 / omission 7 / branch_unhit 3** |
| findings | C3=1, C4=3, C7=1 | **同键同数（零变化）** |

### S.4 预注册判定逐条（11 条机检：8 达标 / 3 越线 / 0 弃权）

| 判据 | 结果 | 依据 |
|---|---|---|
| C1 单变量恰 2 行 | 达标 | `changed_line_count=2` |
| C2 语义零回归 | 达标（**收窄**） | 除 `probe_version` 外仅 2 个**墙钟**字段不同 ⇒ 该行不进任何判决/计数 |
| C3 归档键面 | 达标 | 24→25，新增恰 `symbol_faces`（结构性命中） |
| C4 行覆盖 | **越线（证伪）** | 预注册 921，实测 presence **887** / nonempty **488** |
| C5 可重放性（结构性） | 达标 | 4→2 且 typed 集合与预注册逐字相同 |
| C5b 登记数值面 | **越线（证伪）** | 登记 575 桶值 vs 冻结语料 622；行数 928→997 |
| C6 分类位移（预注册） | **越线（证伪）** | 预注册 omission 9→8，实测 9→**7** |
| C6b 事后修正判据 | 达标 | `{25,7,3}` Σ=35 守恒；`omitted_fields` 7 枚 |
| C7 发现面零变化 | 达标 | 同语料双臂 findings 逐键同数 |
| C8 产物零回归 | 达标 | q10 四件 sha256 逐位未变 |
| C9 负控成对 | 达标 | 对照臂仍判 `ARCHIVE_FACE_FIELD_ABSENT` |

### S.5 诚实边界（不得越读）

1. **三条预注册判据被证伪并如实入档**（C4 / C5b / C6），全部属**预测模型错**，不是被测对象错：
   - C4：把「未早退」当成「有 face」的**充分条件**；实际 presence 另有「行内确有候选符号」前提（`early_returns_before_face_assign=7` 只是必要条件的一半）。
   - C5b：登记数值（575 / absent 79 …）取自 09:08 语料，与冻结语料**不可并列** ⇒ 该子句按证伪入档、**旧口径数值声明作废**（不得用「漂移可解释」降级）。
   - C6：键一旦进白名单即**构造性**移出 `C_producer_dump_omission`，不可能留在 omission ⇒ 我的 8 是推导错误，修正值为 7。
2. **字段存在性 ≠ 字段非空**：`symbol_faces` 在场 887 行 / 非空 488 行 —— 两个数分开报，混用会得出相反的覆盖率结论。
3. **首跑 A/B 作废（VOID）**：两臂跑在**活动工作树**上，且臂副本/产物自身落进被测语料 ⇒ 3571 处差异全属语料漂移 + **自我污染**（器具把测量产物当输入）。已改名 `arm_*_VOID_self_include/` 留档，不参与任何结论。教训：**语料必须冻结快照，测量产物必须落在语料之外**。
4. **本轮只补 2 枚字段**（被已登记读数派生链消费的那 2 枚）；其余 7 枚（`raw/pos_start/pos_end/block_id/path_exists/relocated_lines_ok/relocated_symbols_absent`）仍不落盘 ⇒ **不得**宣称「整体可重放面提升」。
5. `relocated_symbol_faces` 在本语料**分支未命中**（0 命中）⇒ 其可重放性**未被证明**，只登记为待触发口径。
6. 本轮**零产品代码改动** ⇒ 无产品性能/KPI 读数可报；形式校验（`VerificationForm|SkillGeneralization|DevPlanDocRef`）**结转**：对侧 R462 AOT 真跑在场 + `MemAvailable 2097MB < 起手闸 2650MB`。
7. 证据等级 **L1-static**（真源码 AST 派生 + 冻结真语料 + 双臂对照 + 逐位读回）；无编译/测试/AOT ⇒ 不报 L3/L4。

### S.6 下轮候选（L.8 剩余项）

① **L2 器具登记**（对侧空闲 + 全量面复跑）→ ② **形式校验结转清账** → ③ relocated 面**正例语料**（触发该分支以证明可重放；独立预注册轮次）→ ④ 阶段 B 可配语言集（独立预注册轮次）。
