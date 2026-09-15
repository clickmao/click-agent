
---

## 附录 Q · EXP1-Q16：循环累加型计数重放 + 「不可重放」类型化（承附录 P L.8 候选 ③）

> 证据目录：`eval/capability/exp1-q16/{prereg_q16.json,unit_axis_guard.py,verdict_q16.json,evidence_q16.txt,zeroregress_q16.json,selftest_q16.json,selftest_q16.log,run_q16.log,run_q16_v11_preclassify.log,diag_face_rungs.txt}`；登记行 `eval/capability/kpi.jsonl`（EXP1-Q16）。
> 器具：`unit_axis_guard.py v1.3`（v1.0 = 附录 P 冻结件，逐点加法改写；`probe_v260.py` v2.6.0 一字未动；v1.1/v1.2/v1.3 为同轮内演进）。

### Q.1 本轮一步（L.8 候选 ③）

把「循环累加型计数」（`Counter()` + `for … : x[k] += 1`）从**笼统声明不可重放**改为三分：①能给外层绑定链者**真重放**；②给不出者落**类型化原因**（闭集、机检）；③「重放面为空」与「值不等」在 C1 比较层**分离**（口径边界单列）。

### Q.2 修改点（4 个增量，全在器具侧）

1. `collect_counters`：`ast.walk` 无父指针 ⇒ 自建父映射，累加点记录**外层 For 绑定链**（`for c in live_code: for _rung in c[…]: x[_rung] += 1` 现可重放）。
2. `replay()`：失败不再一律吞掉 —— `classify_unreplayable` 归入闭集 `{SELF_REFERENTIAL_CROSS_ARTIFACT, PARAM_SCOPE, POPULATION_NOT_ARCHIVED, LOOP_SHAPE_UNMODELED, ARCHIVE_FACE_FIELD_ABSENT}`；**归不进去即上抛**（fail-closed，不静默跳过）。
3. C1 比较层新增口径边界门：重放面为空 ∧ 登记非空 ∧ 机检到「派生链读的**行字段在归档面全缺**」⇒ `ARCHIVE_FACE_FIELD_ABSENT` 单列（`n_boundary`，不计入 `all_equal`、不判红）；无该证据仍是硬 mismatch。
4. 夹具 10 → 14 格：FX11（嵌套累加正控：C1 必覆盖包装键且相等）、FX12（同夹具但登记值 +1 ⇒ 硬红）、FX14（归档缺字段 ⇒ 边界豁免）、FX13（非累加型不可解析 ⇒ fail-closed exit 3）。

### Q.3 真跑读数（v1.3；零 dotnet，对侧 R455 套件真跑在场）

| 面 | Q15 v1.0 | Q16 v1.3 | 判定 |
|---|---|---|---|
| `probe_stdout.json` | exit 2 · C1 7/7 all_equal · C3=1 C7=1 | **逐位相同** | 零回归 ✓ |
| `attribution_q10.json` | exit 2 · C1 10 · all_equal · C3=1 C4=3 C7=1 | exit 2 · **C1 12**（`n_boundary=2`，可比较者 all_equal=True）· findings 同上 | 零回归 ✓ + 增量 |
| `not_replayable`（attribution） | 4 键（无原因字段） | 4 键**全部带类型化原因**，**无类型跳过 = 0** | 语义升级 |

类型化原因实测：`symbol_face_rungs` / `n_symbol_faces` = `ARCHIVE_FACE_FIELD_ABSENT`（证据：`citations.jsonl` **928 条 live 行**中 `symbol_faces` 出现 **0** 次）；`symbol_occurrences` = `PARAM_SCOPE`；`stale_like_n` = `SELF_REFERENTIAL_CROSS_ARTIFACT`。夹具 **14/14**，两跑 `verdict` 逐字节相同（sha256 `674bb152…`）。

### Q.4 预注册裁定（`zeroregress_q16.json.prereg_verdicts`）

- **成立**：P1（C1 达到面 10→12）、P5（C2–C10 findings / axes / domains / ground_truth 与 Q15 逐位相同）、P6（夹具全绿）、P7（确定性）。
- **否证并收窄宣称**：**P2**（「两键重放值与登记逐位相同」）**不成立** —— 两键只被 C1 **达到**，随即落口径边界 ⇒ **不得宣称「覆盖增益 = 逐位对账」**；**P3** 计数面不成立（4→4）、语义面成立（笼统 → 类型化 + 零无类型跳过）。
- **事后项**（`checks_posthoc`，不计预注册命中）：v1.1 首跑（未分类）在 attribution 上抛 `MEASUREMENT_FAILURE`（`['symbol_face_rungs','n_symbol_faces']`），诊断证实真因是**两类原因被并成一类**（归档面缺字段 ≠ 值不等）⇒ v1.2/v1.3 分离，属**测量层归并缺陷**修正，而非调参放行（预注册判据未改，原始日志留档 `run_q16_v11_preclassify.log`）。

### Q.5 诚实边界

1. **证据等级 L1-static**（真归档语料 + 真源码 AST 派生 + 14 格夹具自检 + 两跑逐字节；无编译/测试/AOT）⇒ 不报 L3/L4。
2. **本轮最有价值的发现**：已登记读数 `n_symbol_faces = 575` / `symbol_face_rungs` 所计数的字段（`symbol_faces`）**不在归档语料里** ⇒ 外部审计者拿归档**无法复算**该读数（判据可达面 < 语料面，第五型）。归因二选一（①落盘块丢字段；②该字段落盘后另行填充）与修法**本轮不做**，只落类型化原因与证据。
3. 嵌套累加**能力**由夹具证明（FX11 正控 / FX12 负控 / FX14 边界 / FX13 fail-closed），**不得**据此宣称真语料上两键可对账。
4. `ARCHIVE_FACE_FIELD_ABSENT` 的机检只认「接收者是外层循环变量」的字段读取（嵌套字典键不会被误认 ⇒ 不把「内层字典缺键」当行字段缺失）。
5. 未改 `src/`、`skills/`、`docs/verification-registry.json`、`eval/capability/instruments.json`、`eval/rover/`、`probe_v260.py`。
6. L2 器具登记仍留待对侧空闲窗口（`instruments_check.py --only` 会覆盖 `instruments-check.json` 既有全量面读数）。
7. 形式校验（`VerificationForm|SkillGeneralization|DevPlanDocRef`）**结转**：对侧执行体在场（R455 套件真跑中）；本轮改动面 = `eval/capability/exp1-q16/` 新增 + 本附录，影响面零。
8. 内部缺陷自曝：v1.1 首版漏了 `enclosing_fors(...) + [node]`（只取祖先、丢了本层）⇒ 外层 iter 被当内层 ⇒ 新夹具立刻抓到；后修复。该条属仪器自检价值实证，非真语料结论。

### Q.6 下轮候选（一步）

① 「归档缺字段」**归因判定**（机检落盘块写点字段集 vs `judge_citation` 返回字段集 ⇒ 判「丢字段」还是「后填」）——本文件**最前**未完成项；② 本器进 L2 器具登记（对侧空闲 + 全量面复跑）；③ L.7 #4 阈值噪声带机检项 / 「先收尾 → 再读闸」落仪器（承 Q12 遗留）；④ 阶段 B（可配语言集）独立预注册轮次。
