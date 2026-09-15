
---

## 附录 R · EXP1-Q17：「归档缺字段」归因判定（承附录 Q L.8 候选 ①，Q.6 最前未完成项）

> 证据目录：`eval/capability/exp1-q17/{prereg_q17.json,archive_field_provenance.py,verdict_q17.json,selftest_q17.json,evidence_q17.txt,run_q17.log}`；登记行 `eval/capability/kpi.jsonl`（EXP1-Q17）。
> 器具：`archive_field_provenance.py v1.0`（新建；`probe_v260.py` v2.6.0 一字未动；零 dotnet）。

### R.1 本轮一步（L.8 候选 ①）

把 Q16 落下的**二选一归因**判死：已登记读数所计数的逐行字段 `symbol_faces` 在归档 `citations.jsonl` 出现 0 次，是 **(①) 落盘块（写点）白名单丢掉了生产者已产出的字段**，还是 **(②) 该字段在落盘后另行填充**。判法 = 真源码 AST 派生三集合（生产者 `P` / 落盘白名单 `D` / 归档实际 `A`）后做 MECE 五分类，逐键归因；产物落盘、夹具双向回放、两跑逐字节。

### R.2 修改点（全在器具侧，产品/依赖零改动）

1. **三集合派生**：`P` = P1（`extract_citations` 内 `out.append({...})` 字面键 14）+ P2（`judge_citation` 内 `rec[...]`/`rec.update` 键 14）+ P3（`run_pass` 内**接收者为外层循环变量**的 `c[...]` 赋值键 7）= **35**；`D` = 定位 `open("citations.jsonl")` 的 with 块 → 其内 `{k: c[k] for k in (…元组…) if k in c}` 的元组字面键 = **26**，并机检 `if k in c` 守卫（即「静默丢弃」机制）；`A` = 真归档逐行键并集 = **24**。
2. **MECE 五类**：`C_archive_foreign_key(∉D∧∈A)` / `C_dump_dead_entry(∈D∧∉P∧∉A)` / `C_dump_producer_branch_unhit(∈D∧∈P∧∉A)` / `C_producer_dump_omission(∈P∧∉D∧∉A)` / `C_written_and_archived(∈D∧∈A)`，按优先级穷尽；**守恒式 `Σ classes == |P∪D∪A|` 机检**。
3. **修法天花板机检**：以数据流派生（名字→名字传递闭包，**循环变量不作传播枢纽**）算「哪些登记键的值表达式传递依赖被漏字段」，再与 Q16 台账的 `not_replayable_typed`（4 键）求交 ⇒ 可解除面。
4. **夹具 15 格**：正控 1（`edge_kind`→类 5）、负控 4（组合：白名单补 face + 归档含 face ⇒ 类 5；单变量：只补白名单 ⇒ 离开类 4；白名单插从不产出键 ⇒ 类 2；归档插外来键 ⇒ 类 1；归档缺条件分支字段 ⇒ 类 3）、fail-closed 3（归档缺失/空/源码缺函数 ⇒ 弃权 exit 3）、守恒 3、域双读数 1、**枢纽规则承重负控 1**。

### R.3 真跑读数（零 dotnet；对侧 R458 AOT publish/ilc 在场）

| 面 | 读数 | 判定 |
|---|---|---|
| 归因 | **① 落盘块丢字段**（写点白名单漏 9 枚生产者字段，由 `if k in c` 静默丢弃） | 判死（②被否证） |
| 类分布 | 归档且白名单 24 · 分工未命中 2 · **漏字段 9** · 白名单死项 0 · 归档外来键 0 · Σ=35=|P∪D∪A| | 守恒 ✓ |
| `symbol_faces` | ∉D ∧ ∈P（`probe_v260.py:778` 赋值）∧ ∈A 0 行 ⇒ `C_producer_dump_omission` | 归因① |
| `relocated_symbol_faces` | 同类目（同源字段同因） | 归因① |
| 漏字段全集（9） | `raw, pos_start, pos_end, block_id, path_exists, relocated_lines_ok, relocated_symbols_absent, relocated_symbol_faces, symbol_faces` | 白名单漏项 |
| 修法天花板 | 依赖 face 字段的登记键 = `{n_symbol_faces, symbol_face_candidates, symbol_face_rungs}`；∩ Q16 非重放 4 键 ⇒ 解除 **2 枚**（`symbol_face_rungs`, `n_symbol_faces`）= **4 → 2** | 预注册 C9 成立 |
| 域（两路独立读数） | 归档 945 行；按 `kind==code ∧ ¬in_code_fence` 复算 live = **928** == 带 `edge_*` 字段行数 **928** | 一致 ✓ |
| 分支条件证据 | `judge_citation` 内 face 赋值前早退 `return rec` = **7** 条 ⇒ 缺字段行是分支产物，复算须沿用 `or {}` 语义 | 与 Q16 「928 行内 0 次」一致 |
| 夹具 / 检查 | **15/15** · 16/16（含 2 事后项 PH1/PH2）· 两跑核心 sha256 逐字节相同 · exit 0 | 全绿 |

### R.4 预注册裁定（`prereg_q17.json`，15 项判据无一否证）

- **逐位命中**：预注册预测 `{archived:24, omission:9, branch_unhit:2, dead_entry:0, foreign:0}`、`universe=35`、漏字段 9 枚名单、`early_returns=7`、归因① **全部与实测逐项相同**。
- **C9 天花板**：预注册「4 → 2」经 Q16 台账 `not_replayable_typed` 交叉核对成立（解除面 `{symbol_face_rungs, n_symbol_faces}`，二者 Q16 原因均为 `ARCHIVE_FACE_FIELD_ABSENT`）。
- **零回归**：`probe_v260.py` / `citations.jsonl` 本轮前后 sha256 逐字节未变；`src/`、`skills/` 无本轮写入（`src/agent/*.cs` 的改动属对侧 R458，非本轮）。

### R.5 诚实边界

1. **证据等级 L1-static**（真源码 AST 派生 + 真归档语料 + 15 格夹具 + 两跑逐字节；无编译/测试/AOT）⇒ 不报 L3/L4。
2. **本轮只判因，不修**：把漏字段加进白名单会改变归档可比性（需重跑探针并重刷归档），属写点改动 ⇒ 独立预注册轮次，本轮零产品改动。
3. **9 枚漏字段中仅 2 枚影响已登记读数**：其余 7 枚（`raw` / `pos_start` / `pos_end` / `block_id` / `path_exists` / `relocated_lines_ok` / `relocated_symbols_absent`）不被任何登记键的派生链消费 ⇒ **不得**把「补齐白名单」说成「整体可重放面提升」，解除面就是 2 枚。
4. **本器自曝 4 处缺陷（全部由自检/真跑首轮抓出，非事后自查）**：① 分类器首版 `universe = P∪D` ⇒ **归档外来键被静默丢弃**（FX07 读到 `class=None` 才暴露）；② `flow_deps` 首版经循环变量 `c` 作枢纽传播 ⇒ **15 键伪依赖**（PH2/FX15 抓出，加「循环变量不作枢纽」规则后收敛为 3 键，负控实测 28→6 证明规则承重）；③ 落盘块定位用 `_str_key(Constant)` 判 DictComp 的 key ⇒ 恒假（真跑前抓到）；④ 文件名在 `with_name("citations.jsonl")` 链上而非 `open()` 实参 ⇒ 首版定位失败（真跑前抓到）。
5. **夹具原位修正 1 处设计缺陷**：FX04 初版（只给合成归档加 `face`）与类优先级自相矛盾（必然判外来键类）⇒ 拆成组合负控 + 单变量负控两格（FX04/FX05）。
6. **L2 器具登记仍留待对侧空闲窗口**；**形式校验（`VerificationForm|SkillGeneralization|DevPlanDocRef`）结转**：对侧 R458 AOT `publish`+`ilc` 真跑在场，`MemAvailable 1441MB` 远低于起手闸（2650MB），本轮不跑 dotnet；改动面 = `eval/capability/exp1-q17/` 新增 + 本附录，影响面零。
7. 口径说明：归档**总行数 945**、**live 域 928**（Q16 登记口径用的就是 live 域）——两者并列报出，不复用单值。

### R.6 下轮候选（一步）

① **落地修法**：把 `symbol_faces` / `relocated_symbol_faces`（可选：其余 7 枚）加进 `citations.jsonl` 落盘白名单 → 重跑探针 → 断言 `n_symbol_faces` / `symbol_face_rungs` 可由归档**独立复算**（Q16 非重放 4 → 2），并同步 `or {}` 语义与域口径；② L2 器具登记（对侧空闲 + 全量面复跑）；③ 形式校验结转清账；④ 阶段 B（可配语言集）独立预注册轮次。
