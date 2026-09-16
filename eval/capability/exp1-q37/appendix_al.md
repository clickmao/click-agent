
## 附录 AL — EXP1-Q37: `l2.instruments-check` rc=1 分诊(同机争用假红) + 面跑前置占用闸 + C14 归属分类 + depth-3 归档自足补法 + 自指成员信息项化 + pin 可比性历史

轮次: **EXP1-Q37** (60m 能力自检作业, 不占主线轮号)。承接附录 **AK.4 四项下轮候选**, 全部并入本轮 (用户令 2026-09-16)。
判决/读数: `eval/capability/exp1-q37/{triage_q36_t9_rc1.json,archive_selfsufficiency_q37.json,pin_history_q37.json,face_q37_t10.json,occupancy_T*.txt}`;
台账: `eval/capability/kpi.jsonl` (EXP1-Q37 行)、`eval/capability/face-scale-ledger.jsonl` (round=EXP1-Q37, headroom=2.952)。

### AL.1 四项候选与真机读数 (AK.4 全并轮)

| # | AK.4 候选 | 状态 | 真机读数 (证据路径) |
|---|---|---|---|
| ① | 面 `l2.instruments-check` 偶发 rc=1 做隔离复跑分诊 + 「兄弟写者在飞」写进面跑前前置闸 | **做** | 分诊判决 **`CONTENTION_FALSE_RED`** (档位 L3): 内层为**断言红** (rc=2, `measurement_ok=True`, `self_dirt=[]`) ∧ 同一命令隔离复跑 `exit_code=0` 零红 ∧ T9 窗口内 4 件 `src/**/*.cs` 被写 + 面 census 记录对侧 `dotnet publish src/agent.host` 与 ILC 在场 ∧ 源码机取 C14 为**唯一**负载耦合判据 (`eval/capability/exp1-q37/triage_q36_t9_rc1.json`); 新增前置闸 `precheck_occupancy.sh` (宽模式 + 两次采样 + 内存门槛 + 落盘再读 + 有界等待); C14 增 `owner_class` 归属 (handwritten/build_artifact, 只进 detail 不改 passed) + FX16/FX17/FX18 三条确定性机理重演夹具 ⇒ `archive_field_provenance --selftest` **checks 15/15 · fixtures 18/18 exit=0** |
| ② | depth-3 归档自足补法 (65 个 live 兜底结点转归档 或 显式登记不可归档理由) + 重跑闭包判定 | **做** | 65 结点裁定 = **36 归档**(逐件 copyfile + sha256 读回核对) / **29 `directory_node`**(闭集理由) / 0 gone / 0 too_large; 归档自足率 **90/155 → 126/155 = 81.29%**; **重跑等价判据**: 归档优先重跑 depth-3 抽取 ⇒ 126 archive / 29 live / 0 gone ∧ 已归档结点 `n_refs` 与 Q35 现场读数**逐结点差 0**; 守恒 4/4; 负控 2/2 (摘除归档 ⇒ 回落 live; 污染副本 ⇒ 等价判据报红) (`eval/capability/exp1-q37/archive_selfsufficiency_q37.py`, `archived_deps_depth3/**`, `archive_selfsufficiency_q37.json`) |
| ③ | 自指成员真值改由**独立轮**核验, 面内降级为信息项 | **做** | 新模块 `eval/capability/face_class_count.py` (计数与判决单一事实源, 自检 **6/6**: 真红仍计入 / 只信息项红不判红且可见 / 声明缺席或理由不在闭集 fail-closed / 无信息项零回归 / 信息项通过也不进分母 / 脏项罚分仍判红); 清单声明 `class=informational ∧ why_informational=self-referential-tree-state` (闭集) 落在 `bind_evidence.{check,committed-state}`; 注入负控**禁止**落在信息项行; 面记录 schema `/5 → /6` (+`member_class`/`passable_*`), 判决只读可判据红线; 面外独立判: `check_committed_state_q30.py` ⇒ `COMMITTED_STATE_CHECK=OK` (HEAD 184 行 / 248 主张 / 211 blob 逐条一致) |
| ④ | 遮蔽族扩容后 pin 历史值不可比, 须在报告面标注 | **做** | `pin_history_q37.py` 由 git 逐修订机取 `TEST_VECTOR_SHA12` + 同提交 `projection_rules.json` 的 round/断点声明 ⇒ 修订 4 (1 个向量机制引入前) / 带向量 3 / **断点 2** (Q35 `bbd6b93aa9f0→b989a219cbf4`; Q36 `b989a219bcf4→07ffb38d2500`, 均 declared); Q37 **未改**投影规则 ⇒ 本轮 pin 与 **Q36 可比**, 与 Q35 及以前**不可比** (`eval/capability/exp1-q37/pin_history_q37.json`) |

### AL.2 候选①分诊链 (T9 rc=1 → 同机争用假红, 判据见 `triage_q36_t9_rc1.py` 预注册 P1–P5)

- **s1** (T9 面行): `l2.instruments-check` rc=1, 子串 OK, L2 全 ok ⇒ 红来自命令 rc, 不是 L2 字段。
- **s2** (内层 scoped 记录, 19:13:02): 内层器具 **rc=2 / substr_ok=false**, 而闸 `measurement_ok=True`、`self_dirt=[]` ⇒ 判定为**断言红**(非弃权、非自身脏项)。
- **s3** (隔离复跑, 20:17:10): 同一命令 `exit_code=0`, `checks_red=[]`, C13 夹具 15/15 ⇒ **不复发**。
- **s4** (并发写者): T9 窗口 (19:11:00–19:15:40) 内 `src/**/*.cs` 被写 4 件 (19:10:53 / 19:10:57 / **19:11:32** / 19:14:16), 面 census 同期记录对侧 `dotnet publish src/agent.host/agent.host.csproj` + ILC + MSBuild node 在场。
- **s5** (唯一负载耦合判据): 由器具源码机取得 C14 判据面 = `src/**/*.cs` ∧ `skills/**/*.md` 中 mtime > 进程起点; 该 glob **含构建产出的 `obj/**.cs`** (AssemblyInfo/GlobalUsings) ⇒ 等价于「窗口内无 dotnet 构建」。
- **判决**: `CONTENTION_FALSE_RED` (**L3**)。**不可取回项** (如实登记, 不冒充): (a) 内层失败的**具体检查项** —— 内层记录只留 rc/substr, 逐检查明细在被同命令覆盖的 `--out` 文件里 (mtime 20:17:10); (b) T9 的 strace 原始轨迹目录已回收 (侧车 `trace_dir` 记 `<runtime>`)。
- **加固**: 前置闸 `precheck_occupancy.sh` (宽模式含 build/publish/test/宿主/服务/面器具 + 连续两次采样 + 内存门槛 + **结果落盘再读** + 有界等待); **单位纪律**: `/proc/meminfo` 给 kB ⇒ 首版把 kB 直比 MB 门槛 ⇒ 恒判空闲, 已改为显式换算 + U1 不变式机检 + 解析失败判 `MEASURE_FAIL` (rc=3), 不放行。

### AL.3 候选②: depth-3 归档自足 (补法 + **重跑等价**判据)

- 兜底 65 结点逐件裁定: **36 归档** (copyfile + 读回 sha256/bytes 断言) / **29 目录结点** (理由 `directory_node`, 闭集) / gone 0 / unreadable 0 / too_large 0 ⇒ 全结点有裁定 (`Σ == 155`)。
- 归档自足率: **126/155 = 81.29%** (旧 **90/155 = 58.06%**)。
- **承重判据 = 重跑等价**: 归档优先重跑 depth-3 抽取 (复用 Q34 `refs_in`/`MAX_SCAN_FILES` 单源) ⇒ 源分布 `archive 126 / live 29 / gone 0`, 已归档结点 `n_refs` 与 Q35 现场读数**逐结点差 0** ⇒ 「自足」定义为**等价** (归档内容不忠 ⇒ 报红), 不是「有副本」。
- 负控 2/2: (a) 把结点从归档面整体摘除 ⇒ 必须回落 `live` (兜底通路非死码); (b) 污染一个有引用的副本 ⇒ 等价判据**必报红** (判据非空心)。另含 N3 空窗正控 (无写入 ⇒ 判绿, 判据非恒红)。
- **口径修正 (旧读数显式作废)**: AK.1 ⑤ 的「覆盖 **90/177 = 50.8%**」把分母取成了 Q35 的 `n_distinct=177` (唯一引用结点数), 而被扫**结点面**是 155 (155 + 21 弃权 = 176 = `n_depth2_nodes`)。正确两栏 = **90/155 = 58.06% (被扫面)** / 90/176 = 51.1% (结点面)。**50.8% 作废**, 不得再用。

### AL.4 候选③: 自指成员信息项化 (面内降级 + 面外独立判)

- 机制: 清单行声明 `class=informational` ⇒ 该成员**照跑照记** (rc/pass 留在 `results`), 但不进**可判据分母**; 判决 (`passable_failed > 0 ⇒ 判红`) 不放宽。声明缺席 / 理由不在闭集 / 声明成员在 results 里缺席 ⇒ `errors` 非空 ⇒ fail-closed 判红。
- 反向控制 (必须两条都在场, 否则信息项机制会变成遮羞布): `face_class_count --selftest` **6/6** = 混合批真红仍计入 (N1) / 只信息项红不判红且计数可见 (N2) / 缺声明 fail-closed (N3) / 无信息项零回归 (N4) / 信息项通过也不进分母 (N5) / 面自身脏项罚分仍判红 (N6)。
- 注入负控**不得**落在信息项行 (否则负控被降级吞掉 ⇒ 空心绿) —— 执行器已按成员类筛选注入目标。
- **顺修 (面自身脏项, 结构性误判)**: T8/T9/T10 三次唯一的 `self_writes` 恒为 Q33 拆出的 `<记录>.runtime.json` **运行期侧车** (t0/t1/trace_dir ⇒ 按设计逐跑变化) ⇒ 纳入 `FACE_OUTPUTS` 白名单 (释放的只是「写事件→本面自身产物」判定, **不是**内容一致性判定; 记录字节面仍由 `face_record_canon` 钉住)。scoped 复核: `side_effects []` / 闸 `red=false verdict=clean` / `self_writes 0`。

### AL.5 附带闭合: 唯一可判据真红 `exp1q31.only-equivalence P1` 的根因与修复

- 现象: T10 可判据面 **24/25**, 红项 = `P1_两路径逐字节等价` (对侧 R495 亦在其登记行 `r494.capability-face-readonly-audit` 里记「余 1 项 only-equivalence P1 仍红(未闭合)」)。
- **根因 (机取)**: 登记表**丢尾 LF** (违反 R481 尾换行契约)。`bind_evidence --apply` 的序列化器 (indent=1 + 尾 LF, SER_ASSERT 二态容忍) 把「补 1 B」写进产物, 而文本外科通路径直保持缺 LF ⇒ 两路径必然不等。实测 A=**341 104 B** / B=**341 103 B**, 首个差异字节落在**文件末尾** (前 341 103 B 逐字节相同)。
- **归属 = 写侧** (外科式改写未按契约补 LF), 不是通路分歧 ⇒ **判据不放宽**。
- 修法: ① 恢复规范形 (补 1 B LF; 补前断言序列化器逐字节复现 + 语义零变化) ② 判据新增**前提检查** `P0_输入规范形` (= 输入已是规范形 ∧ 序列化器逐字节复现; 不成立时把 P1 的红**归因到输入形态**, 修法仍是恢复规范形)。修后 `only_equivalence_guard` **9/9 PASS** (P0/P1 双绿)。

### AL.6 台账与门禁读数

- 面 (T10, 树 `f834137`, 起手闸 IDLE): 可判据 **24/25** + 信息项 1/2 + 1 项面自身脏项罚分 ⇒ rc=1; 唯一真红为 AL.5 的 P1 (**本轮修 + 9/9 复验**), 非器具面回归。scoped 复核 (`--only` 3 成员): 可判据 1/1 + 信息项 2/2 + `side_effects []`。
- 台账: `face-scale-ledger.jsonl` (round=EXP1-Q37, n_instruments=27, n_commands=60, log_bytes=34 094 506, headroom=**2.952**, capped=false, 读回 rows=7 OK)。
- 声明同步: `instruments.json` 5 处 (`exp1q17.archive-field-provenance` sha `cac4530579fd→72d5ea82ffd5`; `l2.instruments-check` sha `b4c5c34cb775→eb9d30eb1de0`; 输入指纹 1 处; 成员类声明 2 行) —— 逐字节复现闸 + 读回校验 (`sync_q37.py`)。
- 登记表 repin: `r444.instrument-acceptance` (`--apply --only --round EXP1-Q37`, SER_ASSERT=OK tail=LF, `R2E_R2F_EXIT=0`); 补尾 LF 后 `bind_evidence --check` 全绿。
- 形式门禁: `env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR dotnet test src/agent.tests/agentframework.tests.csproj --filter "FullyQualifiedName~VerificationForm|FullyQualifiedName~SkillGeneralization|FullyQualifiedName~DevPlanDocRef"` ⇒ **Failed 0 / Passed 14 / Skipped 0 / Total 14 / Duration 791 ms / exit 0** (在登记表 repin 与声明同步**之后**执行; 执行时对侧 R495 真机臂仍在飞, 时长标指示性)。

### AL.7 诚实边界

1. **T11 (干净窗口全量面) 未跑**: 前置闸在对侧 R495 真机臂在飞期间连续两轮判 **BUSY** (常驻服务 n=2 + `MemAvailable` 1.2–1.4 GB ≪ 2600 MB 门槛) ⇒ 本轮面读数 = T10 (含**已修但未在面内复验**的 P1 红)。scoped 复核不是全量面等价的证据。
2. 候选①的判决档位 **L3** 由三件支撑 (隔离复跑不复发 ∧ 唯一负载耦合判据 ∧ 窗口内并发写者), 不是逐检查复现; 内层失败的具体检查项**不可取回** (见 AL.2)。
3. 归档自足的「等价」只在**当前盘面**成立 (副本 = 当时现场字节); 29 件目录结点需现场遍历才能抽引用 ⇒ 明确登记为不可归档, 恢复时仍需现场。
4. 成员类信息项化**不改变**任何成员的真值: 它只把「谁进分母」写清楚; 自指成员真值仍随树态翻转 (以面外核验器为准)。
5. `precheck_occupancy.sh` 的 2600 MB 门槛沿用 Q33 登记值; 本轮 T10 起手 2668 MB (过), T11 起手 1.2–1.4 GB (不过) —— 门槛是**起手闸**, 不是测量精度声明。
6. 未 push (推送暂停令在效): 本轮本地 commit。

### AL.8 下轮候选

1. **干净窗口全量面 T11** (等价于本轮修复的面内复验): 断言 `side_effects []` ∧ 可判据 25/25 ∧ 信息项 2/2 ∧ rc=0。
2. 29 件**目录结点**的归档形态 (目录清单快照是否足以复算抽取) —— 独立预注册轮。
3. `bind_evidence --apply` 的「补 1 B LF」路径应把**契约违反**打成一等可见字段 (现为 stdout 一行 + SER_ASSERT 二态容忍), 并给该轮产物标 `noncanonical_input` 供归属。
4. 信息项成员清单的**反向控制进全量面**: 造「信息项 + 真红混合」注入模式, 断言面仍判红 (现仅单测覆盖)。
5. `R495` 侧 `r494.capability-face-readonly-audit` 行里那条「P1 仍红(未闭合)」记录可据本轮读数闭合 (归属: 对侧登记行 / 本侧实施) —— 由其登记轮自决。
