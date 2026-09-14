# AgentFramework 改进文档 (improvements.md)

> **记录规则 (2026-09-08 重梳)**: 顶部 = 最新版本, 逐版本向下递减; 每节格式统一
> (版本 / 日期 / 状态 / 主题 / 完成记录 / 基线)。v7.x 为历史遗留版本号体系 (v0.x 前身),
> 原始记录见文末「历史遗留」区, 详情走 git log。
>
> **⚠ 文档严谨性铁律 (2026-09-09 用户钦定, 长期有效)**: 凡【以文档为驱动的循环开发迭代方案】
> 中的文档 (README 双语 / api.md / architecture.md / CLI指令说明.md / improvements.md 等),
> 任何修改必须做**全文整体/大区域合法性校验** — 标题与内容对齐 (版本号、批次趋势行归属)、
> 数据时效 (测试数/批号/评测口径)、版本引用一致性、死链检查; **禁止只改局部不做整体校验**。
> 空间位置相邻但语义不同段的错挂 (如旧版本标题下挂新数据) 视同违例。

## v0.60.0 · R440 · 2026-09-15 · 状态: 已完成 · 主题: 一轮任务降幅的**分档实测**（长度梯 + 位置单变量 + 无设备负控）

**完成记录**（零产品源码改动, 被测 = /tmp/pub_r438/agenthost AOT native）:
- 分档实测（远端 token 口径, 同网格 A 臂分母）: 单次 N=1 **−3.95%**（净亏）｜短 N=4 可跳 1/4 **+32.24%**｜中 N=8 **37.90%** / N=12 **37.37%**｜长 N=20 散布 **45.31%** / 晚簇 **48.57%**｜长 N=20 零可跳 **−2.40%**｜负控（无设备·晚簇）**−5.47%**。
- 质量: 全 BRJ 臂 `fn=0 ∧ fp=0 ∧ acc=1.0`（V5 含 7 条未经 r1 实测的新文本 ⇒ 强检验通过）; A/BRJ 的澄清吞并集合逐网格一致。
- 位置单变量: V4（晚簇）− V20（散布）= **+3.26 pt**（晚簇更省）; 预注册模型给 ≈ −1.2 pt ⇒ **C7 FAIL**。
- 预注册判据: **C1/C4/C5/C6 PASS**；**C2/C3/C7 FAIL**，逐条根因**在预测器**: ① A 分母跨网格逐记录下标代理（+9.25%）② 被跳轮在 A 臂的成本被漏计 ③ δ(i) 线性外推。
- 事后校核（checks_posthoc, 单列）: **δ ≡ 77 tok 常数**（5/5 网格逐轮一致）+ 同网格 A 臂分母 ⇒ 重锚模型 **5/5 ≤ 0.47 pt**; 二阶项 = 被跳轮「从未发出内联块」不再回放（散布 2227 tok, 晚簇 ≈0）。
- 器具自捕: `design_check.py` 追回**本轮自身**的 expected 轮号偏移; `predict_r440.py` v1（逐文本匹配 A）自查废弃并留档。

**基线**: HEAD `a0d1ba2` → 本轮提交（未 push, `.git/PUSH_PAUSED` 在位）。器具: `eval/rover/r440/*`。计划: `docs/plans/v0.60.0-r440-length-ladder-measurement.md`。

## EXP1-Q7 · 文档侧定点修复（改写失效路径 + 补退役标记）与「桶归零」的空心绿（60m 自检作业）

**主题**：附录 G.7 结转「把 `relocated` 的 10 条定点可改 + 3 条写法漂移 做文档侧定点修复，并对 `retired_after_write` 引用补退役标记 —— 改动只碰文档，复跑仪器断言两桶归零」。

**判决**：① 文档侧定点修复完成，**只碰 10 个文档**（行数逐文档不变）：`relocated` **13→0**、`stale_path` **21→8**、`retired` **8→21**、`ok` **741→753**、`symbol_absent` **65→66**（唯一迁移项在修前 `relocated_fact_verdict` 即为 `symbol_absent`）、`stale_lines 4`、`waived 70` 未动。② 预注册 P1–P5 **全过**；③ 仪器 v2.3.0 复跑**两跑逐位相同**、自证闸 G1–G6 全 true、`--selftest` exit 0。④ 余 8 条 `stale_path` = 弃权类 `same_commit_as_deletion`（同一删除提交的 8 处），按预注册**零动作**（补标记会把弃权类并入 `retired`，抹掉 G.2 建立的区分）。

**本轮核心发现（自捕测量层缺陷 D1，比修复本身更重要）**：首版修复器按路径**子串**定位插标记 ⇒ 标记落在「路径」与「`:行号`」**之间** ⇒ `CITE_RE` 不再匹配该 token ⇒ **13 条引用从语料中消失**。危险形态在于**目标桶全部"达标"**（`relocated` 13→0 ✓、`stale_path` 21→8 ✓、`exit 0`、两跑逐位相同 ✓）—— **桶判据在缺陷态会放行**。暴露它的是**桶账不平**：`ok +12` 与 `symbol_absent +1` 只能解释 13 条改写，**13 条被标记引用的去向无处安放** ⇒ 语料引用总条数 **922→909**。⇒ 补进预注册的 **P6 计数守恒不变量**：任何改写语料的动作必须断言「引用总条数不变」（修复器层逐文档 + 全语料）。

**修改**：新增 `eval/capability/exp1-q7/{apply_doc_fixes_q7.py(v1.0.0→v1.1.0), prereg_q7.json, edit_plan.json, edit_plan_v100_defect.json, edit_plan_d1_negative_control.json, attribution_q7_{before,after,after_rerun,after_D1repro}.json, selftest_q7_after.txt, README-evidence.md}`；计划文档 **附录 H**；本条目 + `eval/capability/kpi.jsonl`。**未动 `src/`、未动 `skills/`、未动登记表**。

**读数**（修前→修后，仪器 v2.3.0，178 文档 / 594 只读输入逐文件 sha256）：`relocated 13→0`、`stale_path 21→8`、`retired 8→21`、`ok 741→753`、`symbol_absent 65→66`、`stale_lines 4→4`、`waived 70→70`、**引用总条数 922→922**。**负控（可复现）**：`--insert-mode=path_end` 复现 D1 ⇒ 修复器层条数 `582→569`、`count_invariant_ok=false`、`verify_bad=13`（全 `MARK-MISSING`）、`exit 2`；仪器读数落缺陷态档案（**总条数 909，而桶面同样"绿"**）。**绑定仪器真实行为**的读回校验（非文本代理）：13 条改写复跑抽取 + `judge_citation` ⇒ `ok 11 / symbol_absent 1`；13 条标记 ⇒ **`retired` 13/13**。

**基线**：本轮前 HEAD 工作树（本地，未推送；`.git/PUSH_PAUSED` 在位）。证据等级 **L1 静态机检**。形式校验：对侧 30m 主线作业在跑 R440 网格（`eval/rover/r440` + `docs/plans/v0.60.0-r440-*` 为在途产物）⇒ 按「测量纯净闸」**不跑 `dotnet`**，形式校验**结转**（与前两轮同）。

**诚实边界**：① L1 静态，无编译/单测/AOT/真机运行；② 语料是**移动目标**（对侧在改 `src/`/`docs/`）⇒ 读数与 HEAD 绑定，确定性由两跑逐位相同 + 594 输入指纹归因；③ **「两桶归零」按可动作类解读**（`relocated` + `retired_after_write`，两者均 0）——若字面读作 `stale_path→0`，须先裁定那 8 条的语义，**禁止用标记把弃权类洗成 `retired`**；④ `symbol_absent 66` 是全文匹配启发式（非 AST），只作候选不作结论，本轮既未引入新缺陷**也没有修好它**；⑤ 退役标记只声明「路径在 HEAD 不存在 ∧ 删除提交为 HEAD 祖先」，不声明引用何时成形；⑥ 标记/替换串一律由产物派生（仪器常量 + 复核器 `sha7`）并**读回比对码位**，未复现 F.3 的写入通道改写；⑦ 附录 H 正文写入后**复跑仪器零新增引用**（自指控制 922=922）。



## EXP1-Q6 · 全仓失效引用的四级归属复核：时间轴锚点 +「当前不成立」vs「写成时就错」（60m 自检作业）

**主题**：附录 F.5 结转「按同一四级归属**逐条复核全仓剩余 `stale_path 21`**」。本轮把仪器 v2.3.0 判定的 `stale_path` **21** 条 + `relocated` **13** 条（10 文档）**逐条**做完归属复核，并补上仪器未建模的第四级：**时间轴**。

**判决**：① 复核器落地（新件，与仪器解耦，只消费读数 JSON）：`eval/capability/exp1-q6/attribute_failed_refs.py` **v1.2.0**，自证 **18/18** 绿（含**真版本库夹具**三样本：退役前成形 / 退役后成形 / 与退役同提交 ⇒ 必须落**三个不同类**，证明判据两向可分、非恒真非恒假）。② 读数：`stale_path 21` = **retired_after_write 13** + **same_commit_as_deletion 8**，**`dead_after_delete` 0**、`axis_disagreement 0`、`no_deletion_commit 0`；`relocated 13` = **fixable_direct 10** + **path_elision 3**（写法漂移：路径里含省略号）；复核器 **exit 0**。③ 删除侧外部真值齐备：10 个文件**全部**有删除提交且均为 HEAD 祖先（`b00917c` 本地 GGUF 引擎整线退役 9 件 / `af9856b` 插件注册表退役 1 件），全树**无过滤**同名搜索 0 命中（独立于仪器过滤面复核）。

**关键结论（语义澄清）**：**「当前不成立」与「写成时就错」是两个判据**。上一轮只做到前者；本轮补后者后，语料中**「写作时即失效」的引用 = 0** ⇒ 那 21 条引用的**当前无效性**仍由 L-1/L-2/L-3 外部真值证成，属**文档时效维护**对象（补退役标记 / 改写路径），**定级不是缺陷指控**——混为一谈会在批量退役提交上产生成片假红（本轮实测：v1.0.0 锚点取「文档最后修改提交」⇒ 7 条假红；v1.1.0 串级检索未跟随重命名 ⇒ 1 条假红）。

**修改**：新增 `eval/capability/exp1-q6/{attribute_failed_refs.py, result_q6_before.json, result_q6_after_docs.json, attribution_q6_v120.json, selftest_q6_v120.json, make_evidence.py, README-evidence.md}`；计划文档 **附录 G**；本条目 + `eval/capability/kpi.jsonl`。**未动 `src/`、未动 `skills/`、未动登记表**。

**读数**（仪器复跑对照，证明新证据不引入新引用）：`stale_path 21→21`、`relocated 13→13`、`symbol_absent 65→65`、`stale_lines 4→4`（判据 G1–G6 全过，exit 0）⇒ 附录 G 正文**零 `src/` 路径字面量**，自指假红为 0。

**基线**：本轮前 HEAD `7be1d54`（本地，未推送；`.git/PUSH_PAUSED` 在位）。证据等级 **L1 静态机检**。

**诚实边界**：① L1 静态，无编译/测试/真机运行；② 8 条「与退役同提交」是**弃权不是清白**（一次提交既退役文件又写入文档 ⇒ 时间轴同形不可分，要判别需变更前快照，时间戳无用）；③ 时间轴只锚**版本库历史**，未入库文档无锚 ⇒ 弃权（本档 0 条）；④ 语料是**移动目标**（对侧作业在改 `src/`），读数与 HEAD 绑定；⑤ 本轮**三次测量层自捕**（锚点取错层 / 未跟随重命名 / 同提交误落歧义分支），均**先修仪器再谈被测**；⑥ `relocated` 的 10 条定点可改 + 3 条写法漂移**本轮未修**（只复核，不改文档）⇒ 结转下轮。

## EXP1-Q5 · 续引 `[:NNN]` 形态建模（仪器 v2.3.0）+ exp1 §1.4/§1.5/§3.3/§4.2 引用定点修复（60m 自检作业）

**主题**：exp1 档剩余失效引用（附录 D 结转 3 真删 + 9 搬家）＋ 附录 E 结转的「续引 `[:NNN]` 形态建模」。执行顺序：**先补测量盲区，再修文档** —— v2.2.0 既不认出续引形态也无归属规则 ⇒ 本档 **51 条续引从未被检查**（保守漏检）。

**判决**：① 仪器 **v2.3.0** 落地：续引归属四级（T1 反引号内 `Stem.Member` 主干唯一映射 / T2 同行最近前引 / T3 块内前序路径集合唯一 / T4 弃权单列）+ **留痕继承**（同行 ∧ 同路径的带标记引用覆盖该续引）+ 新判据 G6（子探针非退化），自证 **14 → 37/37**；② 本档 `stale_path` **3→0**、`relocated` **9→0**、续引非绿 **5→0**（续引 `ok` 40→44）；③ 全仓 `stale_path` **24→21**、`relocated` **22→13**、`retired` **5→8**、`ok` **724→734**；判据 G1–G6 全过（exit 0）。

**修改**：`eval/capability/exp1-q4/probe_doc_ref_integrity.py`（v2.3.0）；本档 **11 行**修复（3 处真删加退役留痕 / 9 处写法漂移改真实路径 / 1 处续引改显式路径 / 2 处行号事实漂移 `docs/api.md 1409→1410` / 1 处符号名漂移 `SessionMemoryStore→JsonSessionMemoryStore`），`git diff` **11+/11−**，无标题/锚点变更、行号未位移；新增证据 `selftest_v230.json` / `result_v230_{before_fix,after_fix,final}.json` / `ab_diff_v230.md` / `continuations.jsonl` / `gate_check_exp1q5.json` / `form_check_evidence_v230.txt` / `probe_stdout_v230_*.txt`；计划文档 **附录 F** + `eval/capability/kpi.jsonl`。

**读数**（176 文档 / 591 只读输入逐文件 sha256；修前→修后）：本档完整引用非绿 **12→0**（余 2 条 `symbol_absent` 均为附录 E.3 已裁定的**主语型启发式假阳性**，未改文档）；续引 `retired` 6（其中 5 条由**留痕继承**判入：L52 注册表续引 + L67 四条 —— 其锚点引用已登记退役）。

**基线**：本轮前 HEAD `83f04e7`；本轮提交 = `0af65fc`（本地，未推送；`.git/PUSH_PAUSED` 在位）。**形式校验（附录 D/E 三度结转）本轮清账**：`dotnet test --filter "VerificationForm|SkillGeneralization|DevPlanDocRef"` ⇒ **Failed 0 / Passed 13 / Skipped 0 / Total 13 / 338 ms（exit 0）**；**闸门判定理由外显**：`MemAvailable 2668 MB`（阈值 2800）、`pgrep` 计数 2 = Roslyn `VBCSCompiler` 常驻编译服务器 + **自匹配** ⇒ 按「测量纯净闸」原意（防与**在途**构建/测量互撞）判可跑：无在途 `dotnet build/publish/test`、无 `agenthost`、无 `llama-server`、`loadavg 0.10`、对侧工作树 clean。

**诚实边界**：① 证据等级 **L1 静态机检**（无编译/测试/AOT/真机运行）；② 续引 T1–T3 只有**有证据**时才认，不成立一律**弃权单列**（不判红）⇒ 未认领续引不判红；③ 续引**不查符号**（符号归其锚点引用）⇒ 与符号启发式读数分开计；④ T2/T3 是**位置**证据 ⇒ 语义所指与最近前引不一致时会**错锚**（本档 L68 实测一次：续引被错锚到 137 行的 `LlamaCppTextEmbedder.cs`，实际所指为同文件 `ServiceCollectionExtensions.cs:225-242` 的 RAGConfig DI 工厂）⇒ 处置 = **把路径写显式**，不改判据；⑤ 全仓仍有 `stale_path 21 / relocated 13`（集中他档，本档清零）；⑥ 语料是**移动目标**（对侧 30m 作业在改 `src/`），确定性由两跑逐位相同 + 591 输入指纹归因；⑦ 本轮两次踩到**写入通道改写手打字面量**（长字面量里的斜杠被改成点、路径字面量匹配 0 命中）⇒ 替换串一律由**行内 token / 正则**派生、标记常量由**码点**构造；⑧ 「**记录缺陷的文本本身会被机检当活引用**」实测一次（附录 F 初稿把修复前原文写进正文 ⇒ 本档续引 waived +1 / stale_lines +1）⇒ 引用示例必须入**代码围栏**；⑨ 未动 `src/`、未动登记表（`docs/verification-registry.json`）、未新增/改 `skills/`。

## EXP1-Q4 · 引用探针符号归属修复 + exp1 §1.2/§1.3/§4.4 引用定点修复（60m 自检作业）

**主题**：exp1 §1.2/§1.3/§4.4 失效引用（附录 D 结转）。执行顺序：**先修测量，再修文档**——附录 D 的 `symbol_absent` 读数经复核含测量层缺陷，照它改会误杀正确引用。

**判决**：① 仪器缺陷成立（判据被证伪）：符号按**整行**共享 ⇒ 一行多引用时互相污染、虚高。同输入 A/B 证明 **74 条** `symbol_absent → ok`、**零** `ok → 非 ok`（无回归；污染是单向虚高 ⇒ 修复不暴露被掩盖的真缺陷，如实登记）。② 本档 §1.2/§1.3/§4.4 定点修复完成：`stale_path` **5→0**（5 条全部改注退役留痕）、`relocated` **5→0**（改真实路径）、`symbol_absent` 3→2（余 2 条经 grep 复核裁定为**主语型启发式误报**，未改文档）；整档 `stale_path` 8→3、`relocated` 14→9、`symbol_absent` 18→2。

**修改**：仪器 **v2.2.0**（`eval/capability/exp1-q4/probe_doc_ref_integrity.py`）——符号**逐引用就近归属**（整行配对一次，防窗口切片错位）+ 新增 `retired` 判定（显式 `【已删 <commit>】`/`【已退役 <commit>/<R>】` 标记，60 字符窗且不越相邻引用）+ `--selftest` **14/14**（正控/负控各 5 类）；本档 9 行修复（8+/8−，无标题/锚点变更）；计划文档 附录 E + 本条目 + backlog 状态行 + `eval/capability/kpi.jsonl`。

**读数**（174 文档 / 同输入 A/B，语料 905→906 条）：`ok` 651 → 709 → **716**；`symbol_absent` 124 → 66 → 65；`stale_path` 29 → 29 → **24**；`relocated` 27 → 27 → **22**；`retired` 0 → 0 → **5**；`relocated_fact ok` 12 → **25**。

**基线**：本轮前 HEAD `d84ccf2`（本地提交，未推送；本轮提交主题 = `EXP1-Q4: 引用探针符号归属修复 + 本档 §1.2/§1.3/§4.4 引用定点修复`）。**形式校验本轮未跑**：对侧 `agenthost` + 2×`llama-server` 在跑、`MemAvailable 1702 MB < 2800 MB` 闸 ⇒ 按「批测与 build 互斥」避让并**结转**（命令见 exp1 附录 D）。

**诚实边界**：① 证据等级 **L1 静态机检**；② `retired` 是**约定标记**（判据绑"标记出现"，负控 = 无标记或标记越窗仍判 `stale_path`）；③ 归属修复偏差方向为**保守漏检**（符号未被任何引用窗口认领时不做检查）⇒ 下轮候选 = 续引 `[:NNN]` 形态建模；④ 本档仍有 3 条真删 + 9 条搬家（§1.4/§1.5/§3.3/§4.2）；⑤ 本轮未动 `src/`、未动登记表与技能。

## EXP1-Q2 · 计划前提核验：被引契约已删 + 文档引用事实机检（60m 自检作业）

**主题**：exp1 §8-Q2（插件 API 是否引入 manifest + `schema_version`）——先把「复用既有契约（不新造）」这个**前提**核验掉，再谈选项。

**判决**：**前提为假**（机器判）。`ICapabilityPlugin` / `PluginExecutionResult` / `CapabilityPluginRegistry` 在当前 `src/**/*.cs` 出现 **0 次**（正控 `IResponseSegmentPlugin` 24 / `CapabilityScanner` 12 / `PythonArtifactPlugin` 19 证明计数器非恒 0）；`src/agent/registry/CapabilityPlugin.cs`（118 行）与 `src/agent.tests/CapabilityPluginTests.cs`（75 行）在 **af9856b**（2026-09-13, v0.23.0 R386/R387）被删除，且该提交是 HEAD 祖先。

**根因**：exp1 §1.2/§1.3 是按 `docs/reports/r385/capability-inventory.md` 抄写的 r385 盘点，**早于** R386/R387（契约删除）与 **b00917c**（2026-09-14, R408「本地 GGUF 引擎整线退役」，70 文件 / −11,039 行，`BgeCpuEmbedder`+`src/agent.embedcpu/` 整条线）⇒ 整节承载实现已不存在或被重排（本仓并存 `src/agent.<模块>/` 与 `src/agent/<模块>/` 两种写法）。

**修改**（零产品源码改动、零 dotnet）：新增 `eval/capability/exp1-q2/{probe_doc_ref_integrity.py(v2.1.0), selftest_doc_ref_integrity.py(21 项自证)}` + `result.json`/`citations.jsonl`/`selftest_result.json`/`git_deletion_evidence.txt`/`probe_stdout.txt`/`append_kpi.py`；计划文档补 附录 D + §1.2/§1.3 校正块 + §4.4 前提证伪块 + §8-Q2 行。

**读数**（174 文档 / 896 条 live 代码引用 / 589 只读输入逐文件 sha256 指纹）：`ok` 649 · `symbol_absent` 119（启发式候选）· `waived` 68（弃权）· `stale_lines` 4 · **`stale_path` 29（真删）** · **`relocated` 27（搬家）**；本档自身 = 真删 8 + 搬家 21。裁定数据：capability-id 分派契约 **0** / 带版本字段契约 **0** / manifest 先例 **0**（DI 静态注册 53）⇒ D1 `no_existing_carrier`（契约须新建，新建即带 `schema_version` 零迁移成本）、D2 `needs_new_loader`（**不推荐** manifest 形态）。

**仪器缺陷（本轮自捕两处 + 自检一处）**：① v1 把无目录裸文件名判 `stale_path`（首读 **389 条虚高**）⇒ 三级归属 + 弃权单列；② v2 未区分**已删除**与**树内搬家** ⇒ 第四级 `relocated`（0 候选才判真删）；③ 自检抓出「不存在的仓库被判红（应弃权）」⇒ 前置结构检查 + 测量有效性闸。修后仪器自证 **21/21 绿**。

**基线**：HEAD `053edbb`。**形式校验（附录 C 三度结转）本轮补跑清账**：取得对侧空闲窗口后执行 `dotnet test --filter "VerificationForm|SkillGeneralization|DevPlanDocRef"` ⇒ **Failed 0 / Passed 13 / Total 13（914 ms, exit 0）**，证据 `eval/capability/exp1-q2/form_check_evidence.txt`（起跑条件：对侧近 3 min 无产品源码写入、`MemAvailable ≈ 2.6 GB`）。前两次因对侧在途构建/正在编辑产品源码按「批测与 build 互斥」避让，记录在案。

**诚实边界**：① 证据等级 **L1 静态机检**（无编译/测试/AOT）；② `symbol_absent` 是全文匹配启发式，不作结论；③ 只判「引用事实是否成立」，不评价计划内容对错；④ 本机读数是对移动目标（对侧在改 `src/`）的快照，确定性由两跑 + 输入指纹归因证明；⑤ 与附录 C 旧登记「引用路径 6/6 存在」冲突：旧口径过窄，**作废不再引用**（口径变更已登记）。

---

## R433 · 文档跑测链复位 + 取码产物通道（同题假红裁决）

**主题**：用户纠偏令——「仔细审查有没有偏离主题…没怎么严格执行文档中的跑测计划，不看数据只开发是不行的」⇒ 回到 `eval/probe/README.md` 跑测链执行并看数据。

**偏离审查（机检）**：KPI sink `data/probe/kpi.jsonl` 停摆 ~21h（末行 09-13T23:20, 6 行），run 摘要 30 份中 24 份未打点；exp14 M6「扩族+常态化」仍 ⏳；近 8 轮（R424–R432）读数只进 `eval/capability/kpi.jsonl`、**0 行进 KPI sink**。

**判决**：**PASS（链复位）** ∧ 裁决「同题质量无退化」。冻结题集 sha `b8e796a6d803918d`：基线 09-13 `1.0000`(36/36, 215.01s) → 旧仪器 run1/run2 **`0.6944`**（各 1 题 `syntax_error`, 题不同）→ 修后 fix/fix2 **`1.0000`**(36/36)；抗饱和族 3/3（43/43）；判别力负控三族整题 **0/3**（topo_dfs 0.4359 / vm_noerr 0.6250 / json_loose 0.7037 用例级）。

**根因**：判分取码取自**渲染后的对话转录**（TUI 吃掉围栏与 `__x__`, 候选只剩装饰片段 ⇒ `SyntaxError: invalid character '｜' (U+FF5C)`），而产品遥测 `script_artifact` 已记 `origin=fenced` + `compile_valid=true`（3/3 程序题）⇒ **旧读数 100% 假红**。

**修改**（本侧仅评估面, 零产品源码）：`eval/probe/grade.py` 取码新增落盘产物外部真值通道 + `code_source` 可见；`eval/probe/run_probe.py` 遥测收割产物（闭区间进程窗口 ±0.25s, 时间戳 7 位小数容错且不可解析 fail-closed）。自检 `grade` **34/34**、`run_probe` **29/29**（新增 6 条含正/负控）。

**台账复位**：`scripts/kpi_probe.py` 追加 `data/probe/kpi.jsonl` **6 → 14 行**（+8）；A/B 段「同批题集 ⇒ Δ 可比」质量 Δ `+0.0000`；成本 `tokens/题` 6021.8(旧 run1) / 6001.3(fix) / 6032.7(fix2)，墙钟均 15108/20362/31652 ms。

**基线**：`/tmp/pub_r433/agenthost`（HEAD 发布, IL 告警 0, sha256 `a2b3f421…`, 15,184,624 B）。

**诚实边界**：① 不宣称 token 变化（基线在遥测窗口外 ⇒ `tok/题 = n/a`; fix 臂间 6.0k–9.2k 落在远端模型噪声带）；② run2 假红只证「同机制、同 mode、同病因」；③ 墙钟方差 91.97→191.57s ⇒ 不作能力判据；④ 离线复放归属不精确 ⇒ 只作机制验证、不采信为读数；⑤ 抗饱和族题集 sha 与 R417 不同 ⇒ 该行非同题 A/B；⑥ 单机单次。

## R432 · 门判判别力与确定性成对（残余带内）

**主题**：补 R429 诚实边界 ④（判别力负控落空）——钉死判定路径后，门**还能不能区分**「新诉求 / 无新诉求」，且同文重复逐位恒定。

**判决**：臂 2 = **FAIL**（规则：PASS = C1 and C2ack and C2cont and C3 and C4 and C5; PARTIAL = (not C1) and C1p and C2ack and C2cont and C3 and C4 and C5; FAIL = (not C3) or (not C4) or (not C5); UNDECIDED = no r1 reading）；臂 1 = n/a（族位错配，非仪器失效）。

**臂 2 机检读数**：门记录 12（r1 11 / 机械 1）；r1 判决 ["Skip", "Skip", "Skip", "Skip", "Skip", "Skip", "Skip", "Skip", "Skip", "Skip", "Skip"]；raw_len ["474", "474", "323", "323", "185", "185", "185", "185", "261", "261", "170"]；进门位 [1, 2, 4, 6, 8, 10, 11, 12, 13, 14, 16, 18]；归因 alignment=True attribution=False；远端调用 9 / token_est 2434

**基线**：R430 同文 4 次门判 raw 同一（127/127/127/127）且判决 Skip×4（确定性已证）。

**仪器**：新增门判定**时间窗对齐**（telemetry ts 落入轮时间窗，废弃 secs>=5 位置启发式）；实测可达位偏移 = 奇数位（seed 轮问询被下一轮 ask 消费）。

**撞号登记**：R431 被对侧并发作业先占（未提交工作树）⇒ 本侧让号至 R432 / v0.53.0。

**证据**：`eval/rover/r432/README-evidence.md`

---

## R430 · 判定输入指纹 ⇒ 服务端总槽位：决策路径**逐位可复现**（R429 遗留 P5c 收口）

**主题**：把 R429 的「弱宣称（判定**输入**不可复现）」升级为**强结论（同一输入 ⇒ 逐字节同一输出）**。

**因果链**（证据：`eval/rover/r430/README-evidence.md`，由机检 JSON/日志生成）
1. 只观测地加**输入指纹**三层：prompt（送达服务端的渲染后文本）/ 请求体（全字段 JSON）/ 角色种子。
2. 真机（臂 C / k8r，改动前二进制）：4 次门判 `prompt_sha`、`request_sha` **各只有 1 种取值**，
   而输出 raw 逐字节哈希 **4 种**（122/129/113/111）⇒ 输入恒定、漂移在**引擎侧**（H1 证伪）。
3. 机制（传输级探针 `concurrent_probe_v2.py`）：本仓库 llama.cpp 构建 `-np` **默认 = 4 槽**
   （启动日志 `n_slots = 4` 实证）⇒ 门判与关系判官等**并发在途**请求进同一批 ⇒ 每序列批形状/分块
   随调用序列变化 ⇒ 浮点归约顺序变 ⇒ 同一输入走出不同轨迹（105/105/108 tok；串行基线 75）。
4. 修法：本地通道服务端**显式** `-np 1`（真串行；绝不依赖构建默认）⇒ 并发探针 3/3 逐位相同；
   真机同文 4 次门判 raw 逐字节**同一**（sha16 `340ba10faeb3a0a8` ×4），判定仍 `Skip×4`，cache_n 恒 0。

**产出**

| 产出 | 路径 | 机检读数 |
|---|---|---|
| 输入指纹（四层贯通，只观测） | `src/agent.modelqueue/LocalInputFingerprint.cs` + `LlamaCppClient`/`LlamaCppTextGenerator`/`LlamaCppLocalGenerationPort`/`ModelQueueRouter`/`IndustrialAgentV2` | 门判遥测新增 `prompt_sha`/`request_sha`/`req_fields`/`role_seed_sha`；默认路径零回归 |
| 显式总槽位 | `LlamaServerHost.BuildArgumentList`（纯函数）+ `LlamaServerOptions.Parallel=1` + `ModelCatalog local.parallel` + DI 接线 | `-np` **无条件**出现，默认 1；`Parallel≤0` 夹到 1 |
| 新测 | `src/agent.tests/{DecisionPromptFingerprintTests,LocalServerParallelTests}.cs` | 门禁子集 **26/26**；全量 **1242/1242** |
| 机制探针 | `eval/rover/r430/{concurrent_probe_v2.py,probe-r430-concurrent-v2.json,server-probe.log}` | P1 串行同一；P2 并发变体 2；P4 强制 `-np 1` 变体 1 |
| 真机两臂 | `eval/rover/r430/{verdict-C-k8r-r430post1.json,verdict-C-k8r-r430fix1.json}` | pre 4 种 raw / fix 4/4 同一；KPI 远端 2→1、token 2053→1996 |
| 形态 | `/tmp/pub_r430b/agenthost` | IL 警告 **0**；15,180,528 B；sha `bb104dd7…`；V0 闸 AOT 原生 + IL 负控拒 |

**判据（预注册，见 `docs/plans/v0.51.0-r430-input-fingerprint.md`）**：P1 串行同一 ∧ P2 并发可复现漂移
∧ P3 输入指纹恒定 ∧ P4 强制 `-np 1` 后同一 ∧ P5 判定与 KPI 不退化 ⇒ **PASS**（P3 前置在前，落在 H2 分支）。

**诚实边界**：① 未测修法后判定/回复**质量**变化（只测可复现性与 KPI 计数）；② `-np 1` 的代价是本地通道真串行，
墙钟增量未量化上限；③ G3（`-np 2` + `id_slot`）本次亦稳定，但依赖每次调用钉槽位 ⇒ 只作备选记录；
④ 探针 v1 有「渲染早于起服务」与末段取值 bug（v2 已修并增量落盘）；⑤ 单机单次读数。

**下轮候选**：① 门判与判官在 `-np 1` 下的墙钟/排队曲线（量化串行化代价）；② 打点把规则层单列 `rule`；
③ 构造能进 r1 门的新诉求网格（补 R429 判别力负控缺口）；④ `docs/improvements.md` 更早区段（R416/R412/R403 等）仍在乱序位，待重排。

## R429 · 决策路径缓存态钉死（门判 / 关系判官）

**问题（因果链）**：门判与关系判官共用同一个本地推理进程的**单 slot 前缀缓存**（`LlamaCppLocalGenerationPort` 一律 `CompletionReuse.Session`）
⇒ 「缓存命中多少」由**上一次调用了什么**决定（单飞信号量只排除并发，排除不了调用序列）
⇒ 同一 prompt 的生成序列随缓存态漂移 ⇒ **判定不可复现**（R426 诚实边界 ① 的 k8 门判翻转）。

**机制取证（传输级，N=5 轮，同一条 gate prompt）**：cache 开 ⇒ `warm/back/mix/mix2` = `197/197/97/197` token（cache_n `226/226/213/226`），
每轮复现同一形态；cache 关 ⇒ `off1/off2/off3` = `180/180/180`（cache_n 恒 0），5/5 轮逐位相同。
⇒ **旧式必红 ∧ 新式必绿**（P1/P2/P3 过）。

**产品级取证（真角色 + 真链，同文重复网格）**：同一条用户消息被问到 r1 门 4 次 ——
改动前 `Pass/Skip/Skip/Skip`（raw_len `148/106/247/102`，判定与文本都不恒定）；改动后 `Skip×4`（`cache_n` 恒 0、`pinned` 1→4），
同配置重复轮仍 `Skip×4`。远端调用 **4 → 2~3**、token **4243 → 2053~2101**（−51.6%）。
归因机检：`alignment_ok=true ∧ attribution_ok=true`（顺序分区 + 回复形态交叉校验）。

**改动**：`LocalGenerationRequest.CacheReuse`（默认 true = 逐位零回归）+ `CompletionProfiles.ReuseFor`（唯一映射点）
+ 门判/判官两处显式 `CacheReuse=false` + `TurnGate.CachePinned`/`LastCachedTokens`、`RelationJudgeCounters.CachePinned`
+ 门判 telemetry `cache_n`/`pinned` + 新测 7 例 + repo skill `decision-path-determinism`。

**诚实边界**：① P4 **未过**——传输级 20 次 cache-on 门判全为 P，未观测到 S/P 翻转 ⇒ 只证「判定**输入**不可复现」（弱宣称）；
② P5c **证伪**——钉死后 raw_len 仍 4 种取值（`113/105/102/100`；重复轮 `128/108/111/113`）⇒ 文本**逐位**复现未达成，
宣称收窄为「判定结论恒定」；③ 本地判官在本配置**未生效**（2/2 `remote_fallback`、45/66 s，被门判占满单飞槽）；
④ 判别力负控落空（k8p 的新诉求消息走「[隔离任务]」旁路，没进 r1 门）⇒ 「钉死后门仍能 Pass」**无证据**；
⑤ 传输级 prompt 由产物代码重建（角色种子等长占位）；⑥ KPI 有轮间抖动（远端调用 2 vs 3）。

**下轮候选**：① 逐位可复现的残余来源（采样档 / 线程归约 / 服务端状态）；② 门与判官的**真隔离**（独立 slot `id_slot` 或独立进程，
本轮只证「关缓存」这一种隔离）；③ 构造能进 r1 门的新诉求网格（补判别力负控）；④ 打点把规则层单列 `rule`。
## R428 · 同文折叠（排序/去重层）：R427 根因判定的产品落地

- **前置因果**: R427 机检坐实「残留并列对 = 同文重复」（位置逐位差 0/335、Jaccard 1.0）⇒ 同文对**任何**打分族恒同分 ⇒ 出口在**排序/去重层**。「换信号族」对该对为伪命题 ⇒ 本轮改的是排序/去重，而非打分。
- **变更集**: `src/agent/session/SessionHistorySearch.cs`（`Hit.CollapsedDuplicates`；`Search` 第 4 步**同文折叠**；`Render` 输出 `同文副本+N`）+ `src/agent.tests/SessionHistorySearchTests.cs`（+6 例）。
- **零参数设计**: 无阈值/权重/开关；折叠条件 = 规范化正文**逐字符相等**；保留者 = 既有全序（score desc → `SessionId` Ordinal asc）首者；折叠数**可见**（字段 + 渲染）。
- **真机成对裁决 = PASS**（C1–C7 + C2b 全绿；判据 T0 冻结于 2026-09-14T10:17:22Z，先于跑测）:

| 语料 | N 臂（pre-fix，sha `2d363b6d132b06e2`） | T 臂（treated，sha `c547b0bec5b8fbf8`） |
|---|---|---|
| A（冻结，含同文对） | cli-6bf6dc8d 0.2798 → probe-0914125816-p004 0.1408 → probe-0914125831-p005 0.1408 | cli-6bf6dc8d 0.2798 → probe-0914125816-p004 0.1408（`同文副本+1` on p004） |
| D（不同文同分·负控） | r428-d1 0.2284 → r428-d2 0.2284 | r428-d1 0.2284 → r428-d2 0.2284（无折叠标记） |

- **臂身份自证（C1）**: N 臂读数与 R423 verdict 已落档的 `T_treated\|A` **逐位相同** ⇒ 两臂唯一变量 = 本轮 diff。
- **闭式**: 同文组 `[probe-0914125816-p004, probe-0914125831-p005]` ⇒ 保留者**预测 = 观测 = `probe-0914125816-p004`**（Ordinal 较小）；折叠出 = `probe-0914125831-p005`。
- **不变量**: 全部保留者分数与 N 臂**逐位相同**（含 `cli-6bf6dc8d` 0.2798）；`llm_call` 打点 = 0；每查询恰 1 条 `recall_query`；渲染声明命中数 == 实际命中行数；语料**逐字节未被改动**。
- **诚实边界（不宣称）**: ① 证的是**去重层行为**，不是召回质量提升；② 被折叠会话的 **id 不可见**（只计数为 `同文副本+N`）⇒ 若需 id 级可追溯，须让 `Hit` 携带被折叠 id 列表（本轮刻意不做，避免改渲染契约）；③ 折叠在 `topK` **之前** ⇒ 会改变原可能进入 topK 末位的候选（对「列出全部相关会话 id」类需求是行为变更）；④ 未测：>3 文档的真实长库内存/时延、**近同文**（非逐字符相同）去重、`/recall` 之外的路径。
- **产物**: `eval/capability/r428/{run_r428.py, verdict-r428.json, README-evidence.md, stdout-*}`；计划 `docs/plans/v0.49.0-r428-duplicate-collapse.md`。
- **下轮候选**: ① 被折叠 id 可见化（渲染/打点）；② **近同文**去重（须先过 R427 skill 闸：并列先判同一性 + 可分性预检）；③ R426 遗留首要：门与判官**争用隔离**。

## R427 — 「词袋计数族并列」根因判定：并列对**同文**，且 R423 闭式基线取自呈现精度（零产品改动）

- **靶点**: R423 收口时登记的残留并列对（`p004`/`p005`，`distinct 90/90 ∧ tf(存在) 4/4`）被判为「词袋计数族不可分边界」，并留下「换信号族（语义/位置）」的下轮候选。本轮**先做可分性预检**。
- **判决**: **PREMISE-REFUTED** —— 靶点前提不成立，**不进入实现**（止损一轮）。零构建、零测量、零产品源码改动。
- **F1（承重）**: 该并列对**内容重复** —— 检索正文逐词元相同（位置差 0/335，Jaccard 1.0）⇒ 任何打分族都不可能分开同文文档 ⇒ 「换信号族」对该对为伪命题，正确落点在**排序/去重层**（确定性 tie-break / 同文折叠）。
- **F2（承重）**: R423 的 A 臂闭式基线 = `0.059 × TfSat(4)` **精确等于**其登记值 0.14079136730607356（0.059 是 R422 的两位小数呈现值）；全精度应为 0.14076436276343704（基数 0.05898868348219042）⇒ 该基线属**口径混算**；R423 的比值判据与 B 臂读数不受影响。
- **F3/F4**: 位置族在**构造**样本上可分且零参数闭式一致（ratio 1.46875 精确），但在真实语料**无判定样本**（不存在非同文的并列对）⇒ 增益未证；新边界 = 「同 `distinct` ∧ 同 `tf` ∧ 同 `df` ∧ 同首现相对位置」时位置族亦并列。
- **判据**: P0 口径对齐（pin 精确重现）、P0b 基线溯源精确等式、P1 并列复现、P1b 同文检测、P2 位置族在真实对可分（**FAIL = 发现本身**）、P2b 族非空（fail-closed）、P4 命中集合不变；控制 N1 身份、N3 新边界。全绿除 P2。
- **仪器事故 2 起**: ① 首版 P0 用 5e-7 容差对比**呈现精度**已发布值 ⇒ 假红，修 = 容差按半 ulp + 单列 P0b 精确溯源；② 构造样本用「ASCII 词+空格」⇒ `Normalize` 剥空白致整段粘成单 token，`|d.Tokens|` 3 vs 2 ⇒ 前提不成立，修 = 改 CJK 二元组族 + `synthetic_valid` fail-closed。
- **轮号碰撞（一等事件）**: R426 由并发执行体占用（`eval/rover/r426/budget-{A,B,C,D}-k6-r426b1.json` 17:54–17:58 仍在写入）⇒ 本侧**让号取 R427**，未触碰对侧产物。
- **共享文档破坏（一等事件，已修）**: 本节的写入被并发写入者以「逐字符换行」形态落盘（1,512 行 × 1 字符）⇒ **行级判读全部假阴性**（`grep R427` = 0 而那两行文本其实都在）。修复 = 按「逐字符拼接等同性」机器证明后重排为正常行；⚠️ 后续任何写入 `improvements.md` 的轮次都必须做**行结构检测**（1 字符行连跑即判坏）。
- **产物**: `eval/capability/r427/{precheck_position.py, precheck-r427.json, summarize_r427.py, README-evidence.md, detect_line_explosion.py}`；`docs/plans/v0.48.0-r427-duplicate-tie-precheck.md`。
- **下轮预注册（R428）**: 确定性 tie-break / 同文折叠（排序层），真机成对 AOT；判据 = 同分同文两条命中存在与输入列举顺序无关的全序 ∧ 非同文同分对误折叠 = 0（负控）∧ 命中集合与排序不变量成对机检。

## R426 · 关系判官（CorrectionDetector L2 微判定）本地化 —— 「每轮一次 ~45 tok 远端小调用」清零

- **靶点（用户令 KPI 的直接残余项）**: R425 已证「门跳过主调用」，但**跳过轮仍残留 1 次远端判官调用**（R425 证据里 k8 格 3 次调用**全是**判官）⇒ 本轮的 1 步 = 把该微判定的 caller 换成 r1 本地优先。
- **改动**: `ModelCatalog.cs` 增 `local.relation_judge` 键（默认 false）；`LocalGenerationPort.cs` 增 `RelationLetterJudge.TryNormalize`（**只在闭合 `</think>` 之后的结论区**取独立 C/A/N，截断/无字母 ⇒ 未判定；语言无关纯函数）、`RelationJudgeCounters`；`ModelQueueRouter.cs` 增 `RelationJudgeEnabled`/`JudgeRelationLocalAsync`（预算 512 ≠ 调用方 64/128；失败/未判定/记账违规 ⇒ 返回 null ⇒ 调用方**必须**远端兜底）；`IndustrialAgentV2.cs` 判官 caller 选择 + `correction_judge` 打点（source/kind/letter/ms/tokens/prompt_len/msg_head）。
- **读数（桩侧真值, NS=`-r426b1`, AOT sha `538c4e05…`, IL 警告 0, 单测 23/23）**:

| 臂 | k6 调用/判官/tok | k8 调用/判官/tok |
|---|---|---|
| A 本地关 | 10 / 4 / 14081 | 9 / 3 / 13576 |
| B 门开+judge关（R425 口径） | 6 / 4 / 4725 | 3 / 3 / 166 |
| C 门开+judge本地 | **3 / 1 / 4561** | 2 / 1 / 2586 |
| D 负控（无模型） | 10 / 4 / 14081（≡A） | — |

- **判据**: PASS 12 / PARTIAL 2 / FAIL 2 / UNDECIDABLE 1。token 降幅 A→C = **k6 −67.6% / k8 −81.0%**（≥30% 达标）；判官远端调用 4→1、3→1（PARTIAL：残余是 fail-visible 兜底）；负控 D ≡ A 逐位 ⇒ **增益归因 r1 成立**。
- **反例（必须记）**: k8 格出现**门判翻转**（B 6×Skip → C 5×Skip+1×Pass）⇒ +1 次主链调用（≈2524 tok）**超过**判官省下的量级，该格 token 反高于 R425 臂B（2586 vs 166）⇒ C6/C4 **FAIL**。
- **未测到（不宣称）**: 本地判官 vs **真远端判官**的一致性（对手是桩 ⇒ 恒 Neutral，无判别力，判 UNDECIDABLE）；跨轮 +12 tok（0.09%）漂移不追因。
- **下轮首要候选**: ① 门与判官**争用隔离**（同一 r1 端口下门判不稳，代价远超判官收益）；② 打点修复：规则层命中现被记为 `source=remote`（须单列 `rule` + 兜底原因）；③ `allowed_kinds` snake_case 永不命中的白名单静默失效；④ 本地判官人工金标（C/A/N 各 ≥20 条）。
- **产物**: `eval/rover/r426/{run_arm.sh,run_grid.sh,analyze.py,prov_check.py,stub_openai.py,drive_task.py,analyze.py,c11.json,README-evidence.md,verdicts.json}`；`docs/plans/v0.47.0-r426-relation-judge-localization.md`。
- **轮号**: R426 由本支占用（17:48 占用闸空 ⇒ 起跑 17:54）；并发支已按铁律**让号取 R427**（对侧 `improvements.md` 已登记，本侧不改写对侧产物）。

## R425 — 「非实质轮占比 → 降幅」敏感性网格（零产品改动；判决 **PARTIAL**）

**动机**: R424 把「−30%」报成**单点**（50% 占比 → −33.3% 调用 / −58.5% token）。单点不可外推 ⇒ 本轮把口径改成**曲线**：非实质轮占比 k/8 ∈ {12.5%, 25%, 50%, 75%, 100%}，每格真机 AOT 成对（臂 A = 本地通道关 / 臂 B = 门开 + r1 在），另跑归因臂 B′（门开 + 模型缺）。

| 非实质占比 | 远端调用 A→B | token A→B | token 降幅 | 调用降幅 |
|---|---|---|---|---|
  | 1/8 = 12.5% | 10→9 | 14567→12494 | **14.23%** | 10.00% |
  | 2/8 = 25.0% | 10→8 | 14292→9980 | **30.17%** | 20.00% |
  | 4/8 = 50.0% | 9→5 | 14119→4523 | **67.97%** | 44.44% |
  | 6/8 = 75.0% | 10→6 | 14069→4721 | **66.44%** | 40.00% |
  | 8/8 = 100.0% | 9→3 | 13564→166 | **98.78%** | 66.67% |

- **归因**: 臂 B′（无设备）k=6 = 10 调用 / 14,073 token ≈ 臂 A 10 / 14,069（差 0.028%）⇒ **无 r1 则增益归零 ⇒ 增益归因 r1，而非机械门**。
- **判决 PARTIAL（预注册真红，未事后放宽）**: `C_a` 严格单调被 **k=6 66.44% < k=4 67.97%** 证伪；`C_b`（D_k = k·ĉ）被相对误差 24%/29%/43%/7%（容差 15%）证伪 ⇒ **节省不按轮可加、占比不是充分统计量**；`C_c`/`C_g` 被「跳过轮仍残留一次 ~50 token 小调用、该轮回复仍来自远端桩」证伪 ⇒ 门的跳过是**部分跳过**（省主链、留小调用）。**事后判据**（单列）: A 参照假阴性 **0**；可归因跳过轮 12/12 例降 token（其中 10 例降到 0）。
- **宣称收窄**: 本任务族内 **占比 ≥25%** 时 token 降幅 >30%（25%→30.17% 仅擦线；12.5%→14.23% 不达标）⇒ 用户令「≥30%」的**适用面**是「非实质轮占比 ≳25%」，不外推。
- **与 R424 不可比**: 两轮脚本不同（R424 的 8 轮 / A=12 调用；本轮 A=9–10 调用）⇒ 绝对读数不同源，只在本轮内做网格差分。
- **仪器事故 4 起（都是「读数不可信」类，已入档）**: ① 首跑 batch **漏传 `--role`** ⇒ 门未进判，A/B **逐格逐位相等** + 无本地推理时延；源码坐实 `src/agent/IndustrialAgentV2.cs:1464` 要求 `ActiveRole != null` ⇒ **门相关臂必须显式传 role，否则静默测到未门路径**（该批次保留为阴性对照，不作治疗读数）；② 逐轮调用归属按「首个覆盖窗口」⇒ 窗口重叠把整程调用记到第 1 轮，改**顺序分区**后未归属 0；③ 器具 cleanup 未回收框架自启的 `llama-server` ⇒ 11 只孤儿（r1 一只 1.4 GB，`ppid=systemd`），本轮清理并加 `pkill -P $HOST_PID`，b2 跑后残留 **0**；④ 结算器读 `prov-*.json` 路径写错（字段在 `under_test` 下）⇒ 修读取路径，判据未改。
- **形态**: 两臂同一 AOT 产物 `/tmp/pub_r423/agenthost`（15,168,064 B, sha `2d363b6d…`），`prov_check.py` 跑测前 fail-closed（IL 壳负控 rc=131）；**产品源码零改动** ⇒ 未重发布、未重跑全量测试（表单 13/13）。
## R424 — 主线 KPI 的**发布形态身份**修复 + 在 AOT 上复现（零产品改动）

- **起因（身份不可验证）**: R413 台账记 `agenthost_bytes: 15138848 / aot_il_warnings: 0` 并宣称 AOT 读数，但其器具 `eval/rover/r413/run_arm.sh:12` 的被测路径是 `src/agent.host/bin/Release/net10.0/agenthost` = **78,256 B 的 IL apphost 壳**（同目录并存 `agenthost.dll`；`env -i <bin> --version` ⇒ `You must install .NET…` rc=131）。时序亦不合：臂 A/B 落盘 10:57 / 12:04:44，`publish_aot.sh` 产物 mtime **12:07:16** ⇒ AOT 建在测量之后；全仓无 `publish → bin/Release/net10.0/` 拷贝脚本。⇒ R413 读数是 **JIT 中间证据**，`agenthost_bytes` 属事后另做的构建，不是被测对象身份（措辞守界：**不断言「一定不是 AOT」，断言「形态未验证」**）。
- **动作（一步）**: 在**可自证 AOT 产物**（`/tmp/pub_r423/agenthost`, 15,168,064 B, sha256 `2d363b6d…`, IL/trim 警告 **0**）上重跑**逐字相同**的任务脚本，并把「形态自证 + 成对负控」做成**跑测前 fail-closed 硬闸**（V0）。三臂：A（无 local 段）/ B（门开、模型在）/ **B′（门开、`model_path` 指不存在 ⇒ 无设备负控，兼 r1 归因臂）**。
- **真机读数（外部真值 = 桩侧逐请求落盘）**:

  | 臂 | 远端调用 | 远端 token(估) | 跳过轮 |
  |---|---|---|---|
  | A（分母） | 12 | 16,888 | — |
  | B（r1 门） | **8** | **7,007** | 2/4/6/8 |
  | B′（门开·无设备） | 12 | 16,891 | 0 |

  **C1 −33.3% 调用 / C2 −58.5% token（均 ≥30% ✅）**；C3 零假阴性；C4 跳过轮 = 21 字非 LLM 模板；C5 臂 B′ ≡ 臂 A（差 0.018%）；**C6 省下 4 调用 == 4 个非实质轮，且 B′ 无 r1 ⇒ 增益归零 ⇒ 增益归因 r1 而非机械门**。V0/V1/V2 形态与门真身闸全绿 ⇒ **PASS（9 预注册 + 5 事后）**。
- **与 R413 的关系**: 两臂读数**逐位相同**（12/16,888 · 8/7,007）⇒ **该任务上 JIT 与 AOT 读数不可分**；R413 证据的**本体成立**，本轮补的是**身份**。另：R413 登记字节 15,138,848 与本次 15,168,064 **不同源**。
- **role 额外数据（用户令「记得要挂载 role 的额外数据」）**: 调用点 `src/agent/IndustrialAgentV2.cs:1481` = `ActiveRole.Id + "|" + Clip(ActiveRole.ProfileSeed, 80)`；`TurnGateJudge.BuildPrompt`（`LocalGenerationPort.cs:234`）把它作为 `【角色设定】` 插入本地门提示。**实证非空**：桩侧捕获的远端系统提示内含 `【角色:疑问者】你是一个低调但执着的追问者…`（同 run 同字段）。**边界**：成长经历形参 `null` = **未挂**；且门提示内容不可直接观测（下轮加打点）。
- **仪器缺陷 2 起（都是「读数不可信」类）**: ① 器具跑 IL 而台账宣称 AOT（本轮封堵：`eval/rover/r413/run_arm.sh` 现 fail-closed，实测 `rc=2 [REFUSED]`）；② 逐轮调用归属在轮边界对**异步判官调用**有 ±1 轮滑移（已有 `t_start/t_end`+桩 `ts` 口径；总量精确、未归属 0）。⇒ 已登记为下轮候选。
- **命名空间碰撞（一等事件）**: 与并发执行体撞号 R423（对侧 = 检索 tf 饱和，`eval/capability/r423/`）⇒ **本侧让号至 R424**（17:10:36 迁移 `eval/rover/r423/ → eval/rover/r424/`，计划改名 `v0.45.0-r424-aot-mainline-replication.md`）；R423 归对侧；未改写历史、未删对侧产物。根因：启动占用检查未复跑「活动执行体 + 锁 + 目标轮文件 mtime」全序列。
- **计划/证据/登记**: `docs/plans/v0.45.0-r424-aot-mainline-replication.md`（§3–§5 预注册 17:05:36 < 首臂 17:06:23）；`eval/rover/r424/README-evidence.md`（L4）；`docs/verification-registry.json` → `r424.mainline-token-budget-aot-replication`；回归抽查 **47/47**（`--filter FullyQualifiedName~TurnGate`）。
- **下轮候选**: ① 形态闸下沉/统一（标 r413 为历史器具）；② 成长经历块**有界挂载**对假阴/假阳的影响（须成对负控）；③ **占比敏感性网格**（1/8、2/8、4/8、6/8）把 −30% 口径表述为「占比 → 降幅」曲线，替代单点宣称；④ 本地门提示打点（`local_gate_prompt_len`）使挂载可机检。

---

## R423 — 跨会话检索打分：**词元频次饱和** + 可分性预检（R422 §5 预注册项落地）

**版本**: R423 · **日期**: 2026-09-14 · **状态**: 已实施（本地 commit，**未推**）· **判决**: **PASS**（主判据 10/10 绿；含边界登记与两起仪器/流程事故入档）
**主题**: R422 收窄宣称后遗留的「等长文档残差并列」。靶点按 R422 §5 预注册 = 词元频次（tf）信号。

- **★ 可分性预检（先做，且据其结果改写靶点）**: 对 R422 残留并列对取**机检**特征向量（真实存储 Load + 文档构建 + 真实分词器）⇒ 两份长文档 `distinct 90/90 ∧ tf(存在) 4/4` **逐项相等** ⇒ 频次信号对该对**恒为空操作**（数学上恒零，不是"效果有限"）。⇒ 该并列登记为**词袋计数信号族的不可分边界**（需换信号族：语义/位置），本轮**不**作"R422 残留零区分度已消除"的全称宣称，只宣称「等长**但出现次数不同**的文档可分档」。
- **改动**: `SessionHistorySearch.cs:98` 打分分子 `Idf(t) * TfSat(tf)`，`:219` `TfSat(int tf) => 1.0 + Math.Log(tf < 1 ? 1 : tf)`（**因子 ≥1 ⇒ 分数符号不变 ⇒ 命中集合可证不变**；单调不减 ∧ 对数饱和=相对增益递减）；`:203` `CountTokens`，`:75-76` 词元集由计数键派生（**单一真源**，无二次分词口径分叉）。零参数/零配置/零 LLM。
- **判据（预注册，harness 先写后跑）**: C0 语料目录条目集纯净 / C1 六查询命中集两臂逐元素相同 / C2 负控全等 ∧ 治疗分档 / C3 比值 == `1+ln3`（闭式）/ C4 tf=1 逐位不变 ∧ tf=4 == 登记值×`(1+ln4)` ∧ 隐含 tf == 机检钉死值 / C4b 负控读数 == R422 登记值 / C5 极性不退化 / C6 渲染可机读+零 LLM / C7 语料逐字节且只读 → **全绿**；C8（等长同频次仍并列）**单列边界登记**。
- **读数（AOT 成对真机）**: T `/tmp/pub_r423/agenthost`（15,168,064 B，**IL/trim 警告 0**，sha `2d363b6d132b`）vs N `/tmp/pub_r422/agenthost`（sha `55e1ed1a5d45`）。等长可区分对（`|d|=2`，tf 3 vs 1）: N `[0.4901, 0.4901]` **全等**（臂身份自证）→ T `[1.0286, 0.4901]` **分档**，比值 `2.098755` vs 闭式 `2.098612`（相对误差 6.8e-5），隐含 tf `3.000`。R422 冻结语料: tf=1 文档 `0.2798` **逐位不变**（因子单位元）；tf=4 文档 `0.059 → 0.1408 == 登记值×(1+ln4)`（隐含 tf `4.0006`）。
- **★ 首跑预测输入纠错（已归档）**: `verdict-r423-run1-predictor-error.json` 保留 C4 **红** —— 红因是**预测输入人工复算错**（只读 `LongTermMemory` 段 ⇒ tf 算成 2，真值 4），实现行为符合闭式（隐含 tf 实测 4.000）。处置: 预检数字改**机检钉死**（单测 `R423_FrozenCorpus_FeatureVector_IsMachinePinned_NotHandCounted`）+ 新增"隐含 tf == 钉死值"子判据；**判据结构与阈值未改**（不放宽、不为变绿而动实现）。
- **★ 语料目录污染事故（C0 由来）**: `eval/capability/r422/fixture-sessions/sessions/` 空子目录 —— 存储构造即 `Directory.CreateDirectory(<path>/sessions)`（`SessionMemoryStore.cs:19-20`），某次以**语料目录本身**作根构造就地建出。三份语料 sha256 **未变**（== R421 登记），`rmdir` 清除；harness 加固为只取文件 + 新增 C0（条目集纯净机检）。
- **单测/形式校验**: `SessionHistorySearchTests` **26/26**；形式校验（VerificationForm|SkillGeneralization|DevPlanDocRef）**10/10**。
- **登记**: `r423.recall-tf-saturation`(L4)；计划 `docs/plans/v0.44.0-r423-tf-saturation.md`；证据 `eval/capability/r423/{verdict-r423.json,README-evidence.md}`；台账 `eval/capability/kpi.jsonl`。
- **流程教训（语言无关，已抽为 skill）**: ①改进排序/打分类信号的**第一步是对已知并列样本做可分性预检**（信号在该对取值相等 ⇒ 改进恒为空操作 ⇒ 换族或登记边界，别投入实现）；②**预检/预测数字一律机检取值**，人工复算会漏口径（本轮 tf 手算 2 vs 真值 4，被闭式对账当场逮住）；③闭式对账（`比值 == 1+ln tf`）比"看起来分了档"强得多。
- **诚实边界**: ①频次因子对「词元数与出现次数皆相同」者无区分度（不可分边界）；②收益面未量化（真实语料中该形态占比未知）；③`(1+ln tf)` 无参数口径**未做**变体网格/上界 oracle ⇒ 不宣称该靶点最优（BM25 `k1/b` 族未探）；④「整串命中兜底/加成」两条路径不带频次因子（常量赋值），口径局部不一致未评估；⑤`|d|` 仍取去重词元数（R422 §6-2 遗留未做 A/B）。

---

## R422 — 跨会话检索打分校准：**文档长度归一**（R421 §5 预注册项落地）

**版本**: R422 · **日期**: 2026-09-14 · **状态**: 已实施（本地 commit，**未推**）· **判决**: PASS 之外 **PARTIAL**
**主题**: R421 真机暴露的 **打分零区分度**（`/recall 存在` 命中 3 份文档、分数**全等** `0.5596`）——短文与长文并列，排序退化为 sessionId 字典序。本轮按 R421 §5 **预注册靶点**落地文档长度归一。

- **改动**: `src/agent/session/SessionHistorySearch.cs:97-99` —— `score /= Math.Sqrt(qSet.Count) * Math.Sqrt(Math.Max(1, d.Tokens.Count));`（余弦式；**零参数/无语料均值/不改确定性**；除数为正 ⇒ 分数**符号不变** ⇒ 命中集合可证不变）。单测 +2（`SessionHistorySearchTests.cs:322-359`）：词元数 1/3/5 ⇒ 分数**严格递减**；真机语料族上「归一在作用」∧「R421 极性不变量未被破坏」**同时**成立（成对，防一刀切）。
- **判据（预注册：harness 先写后跑，未被结果回改）**: B1 命中集逐元素不变 / B2 分数不再并列 / B3 负控臂全等（臂身份自证）/ B4 极性不退化 / B5 数值对账 / B6 渲染可机读 / B7 零 LLM / B8 语料逐字节且只读。
- **读数（AOT 成对真机）**: T `/tmp/pub_r422/agenthost`（15,159,856 B，**IL/trim 警告 0**）`[0.2798, 0.0590, 0.0590]` vs N `/tmp/pub_r421_pre/agenthost` `[0.5596 ×3]`；对账 `|d|_est=[4.0, 89.96, 89.96]` ⇒ `0.5596/√4=0.2798` ✓、`0.5596/√90=0.0590` ✓（F4 渲染，相对容差 2%）。命中集**逐元素相同**（B1 绿）。
- **★ 预注册判据被证伪（本轮核心诚实项）**: **B2 红** —— 3 份命中里两份**词元数相同**（≈90）⇒ **任何仅依赖文档长度**的归一在数学上都不可能为其分档（残差并列是应然，不是缺陷）；**B5 红** 因容差 0.02 与 **F4 渲染精度**不匹配（事后按 2% 相对容差重算为绿）。⇒ 宣称**收窄**为 `claim_scope`：「分数与文档词元数成反比、召回集合不变；**等长文档仍并列**（后续候选：tf/语义信号）」，**不**作「零区分度已消除」的全称宣称。
- **登记**: `r422.recall-length-norm`(L4, 带 scope 注记 + 预注册失败项如实列出)；`verdict-r422.json` 保留 `pre_registered_failures=[B2,B5]` 与 `checks_posthoc`（事后判据**不与主判据混列**）。
- **附带修复（同血缘召回面，独立登记）**: `src/agent.rag/RAGConfig.cs:706-719`（修前）词袋 embedding = `Math.Abs(word.GetHashCode())`（**进程随机化** ⇒ 同一文档跨进程向量不同 = 落盘索引重启不可复现）+ `(hash + seed * 31337) % dimension`（**可溢出为负** ⇒ `embedding[负]` ⇒ `IndexOutOfRangeException`，栈 `GenerateEmbedding ← IndexAsync`）。取证 = **9 进程样本：红 2 / 绿 7**（概率性 ~20%/进程；量级自证 700 文档 × ~20 token ⇒ 每进程期望溢出 0.2 次）+ **基线对照**（stash 本轮源码后重跑 1176/0/0）证明红与本轮改动无关。修 = FNV-1a 确定性哈希 + **无符号**取模（`RAGRecall.StableHash`/`BucketOf` + `InternalsVisibleTo`）；判据 = **确定性等价类** 4 例（负控：旧公式在该边界输入**确实产负下标 -15** ∧ 新式恒 [0,128)；对抗性 hash 恒非负；与测试侧**独立实现**的 FNV-1a 逐元素相等；端到端词袋召回命中）。**通则**：概率性缺陷不得以「重跑变绿」为判据。
- **诚实边界**: ①`|d|` 只做「词元数」单口径，未 A/B；②事后 2% 容差**不得当主判据复用**；③3 份语料不足以估「等长并列」的实际影响面。

---

## R421 — 跨会话检索**否定极性**：`¬存在 ≠ 存在`（R420 真机缺陷闭合）

**版本**: R421 · **日期**: 2026-09-14 · **状态**: 已实施（本地 commit，**未推**）· **回填标注**: 本节由 `docs/plans/v0.42.0-r421-polarity.md` + `eval/capability/r421/verdict-r421.json` 重建，**读数未改**。
**主题**: R420 真机暴露「`存在`(2 字) 与 `不存在`(3 字) 命中**同一批**文档、分数同为 `1.5660`」⇒ 用户问「X 不存在吗」会收到「关于 X 的文档」，读起来像**肯定**。机理 = CJK 二元组「不存在」包含「存在」⇒ 词面子串重叠被当成同一命题。

- **改动**: `SessionHistorySearch.Tokenize` 对**否定标记**（不/没/未/无/五）自身及**紧邻的 1 个二元组**加 `NegMark`(U+0001) 前缀 —— `Normalize` 丢弃全部控制字符 ⇒ 真实文本不可能产出该前缀 ⇒ **无碰撞**；查询侧与文档侧走**同一** `Tokenize`（**无查询侧特判**）。
- **判据/读数**: 四查询真机成对（T=`/tmp/pub_r421` vs N=`/tmp/pub_r420_pre`）：`不存在` 命中 **3 → 0**，且 N 臂 `不存在` 与 `存在` 命中集**逐元素相同**（缺陷复现）；`存在` 两臂命中集一致（**召回未被打死**）；`llm_call=0`、`recall_query=1`/查询；表单 13/13。
- **排除项（已登记）**: ①否定在句中且距命中词 **>1 字**的作用域扩展；②**打分长度归一** —— 已由 R422 接手（首项仍在册）。

---

## R420 — backlog L2 待办① / L7-G1：跨会话检索**接线**（`SessionHistorySearch` 生产消费点从 0 到 1）

**版本**: R420 · **日期**: 2026-09-14 · **状态**: 已实施（本地 commit，**未推**）
**主题**: `SessionHistorySearch` 于 R370 交付并带 10/10 单测，但**生产消费点为 0**（`grep` 仅命中测试）——"库面实现 + 单测齐" ≠ "已接线"（本仓 ⑧ 类缺口，L7-G1 高优先级）。本轮按循环 branch A 取**最前**未完成计划项，只推进一步：接上唯一合法出口。

- **改动（四表接线，缺一即静默送 LLM）**：① `Known` 白名单 `+= "/recall"`；② `TryRoute` switch 臂返回 `Handled/Command/Argument`；③ 宿主 dispatch 特判（解析 `[topK]` 默认 5 夹取 1–50 → `SessionHistorySearch.StoreSource(_sessionMemoryStore)` → 渲染；**通道级**打点 `recall_query{query_len,topk,hits}`）；④ 新增**可测**静态 `Render(...)`，空命中出显式「无命中」文案（不静默空白）。
- **判据（预注册，C4 ∧ C5 才成立）**：C1–C3 单测 **28/28 PASS**（`/recall` 三元断言 + `KnownCommands` **全集行为探测**（漏臂即红）+ 3 条渲染断言）；C4 真机治疗臂同窗口 `recall_query`=**3** ∧ `llm_call`=**0**；C5 负控臂 = **接线前 AOT 产物**（`/tmp/pub_r414/agenthost`，12:19）同形输入 `recall_query`=**0** ∧ `llm_call`=**1** 且 stdout 无渲染、直接送 LLM。
- **仪器教训（本轮关键）**：CLI 在 `-q` 下**恒定**打印「意图分析/管线执行」⇒ 只读 stdout 会把两条臂都判成"走了主链"，结论**完全相反**。行为类读数一律取通道级打点；"本地指令零 LLM"必须配**接线前产物负控**才不是恒真断言（与 R415「判别力需成对断言」同族）。
- **登记表**：新增 `r420.recall-command-wiring`(L4)；改写前先断言「序列化器逐字节复现原文件」= True 后才程序化插入（diff = 19+/1−，无整份重排），登记表改动后**当轮**跑形式校验。
- **★ 新缺陷（真机暴露，未修，下轮候选）**：打分对**否定**无感 —— `存在`(2 字) 与 `不存在`(3 字) 命中**同一批**文档、分数同为 **1.5660**；`外星词根zzq不存在` 得 2 命中 ⇒ 用户问「X 不存在吗」会收到「关于 X 的文档」，读起来像**肯定**。机理 = 词面子串重叠 + 无否定处理 + 无分数门。与 skill「标记『出现』≠『误用』」同族：**词面重叠 ≠ 语义相关**。
- **诚实边界**：①负控为**产物级**（非源码回滚）；②真机 7 条查询单批单机，只作行为证据、**不构成召回率**；③两条正向查询（`会话记忆`/`向量召回 嵌入`）0 命中 = 语料分布问题（探针题面占据），不与"召回全灭"混同。

---

## R416 — R371-D2 收口：发布产物自包含 config 的**仓库外 cwd 真机验收**（能力自检循环）

**版本**: R416 · **日期**: 2026-09-14 · **状态**: 已实施（本地 commit，**未推**）
**主题**: D2（发布产物不自带 config）的 csproj 复制规则此前已落地，但「自包含」从未从**仓库外 cwd** 真机取证。本轮按能力自检循环 branch A 只推进一步：把该断言升级为可复现的外部真值。

- **harness（不改产品代码）** `eval/rover/r371d2/`：`run_d2_acceptance.sh` 三臂（治疗 / 撤销修复负控 / 修复前产物负控）+ `verdict.py`（6 断言三态裁决，臂缺失或超范围走**弃权**不判红）+ `append_kpi.py`（幂等台账，重跑不污染趋势）。
- **判据（预注册，全外部真值）**：治疗臂（`/tmp/pub_d2/agenthost`，cwd=`/tmp/d2-cwd`，`env -u AGENTFRAMEWORK_CONFIG`）stdout **不得**含「模型目录为空」，**且**必须出现**越过选模**的证据；两路负控**必现**该症状——合取成立才判过。
- **读数**：`verdict-r371d2.json = pass`（6/6）。治疗臂 `rc=0 / 849 B`：输出「prompt 构建完成 ~3385 tokens」并点名 `deepseek-flash` ⇒ 已解析**自带** config 完成选模，失败点后移到凭据未设（**非**配置缺失）；撤销修复负控（移走自带 config）与修复前产物负控**都命中**「模型目录为空」⇒ 断言非恒过。静态自证：cwd 及其 8 级祖先无 config；自带 config 与仓库 config 同源（sha 一致）。
- **登记表**：新增 `r416.release-selfcontained-config`（L4）。等级依据 = **运行期行为 + 两路负控**（注入缺陷必失败），**非** AOT 编译校验——已按 `aot_check_policy=release_tag_only` 在该行写入口径澄清。登记表改动后**当轮**跑形式校验两次：**13/13 PASS**。
- **诚实边界**：①三臂退出码均为 0 ⇒ 该失败**不以退出码体现**，判据只认 stdout 外部真值；②凭据未设，未做真实远端调用（不影响本判据）；③本轮发现**并发兄弟作业**（tag `r416` 探针跑测 12:52:50–12:53:11，仓库外 AOT `/tmp/pub_r414`，读数 35/35 `validity=ok`）——其被测二进制在仓库外，故 build 替换类污染不适用，但其**时间类分量**按指示性看待；轮号 R416 由两支共用，命名段已区分（`eval/rover/r371d2` vs `eval/rover/r416` + `data/probe/*-r416-*`）。

## R415 — 链级钉死「前置门入参 = 用户本轮原文」：把 R413 的防线从源码级升级为行为级（外部真值）

**版本**: R415 · **日期**: 2026-09-14 · **状态**: 已实施（本地 commit，**未推**）
**主题**: R413 的前置门增益曾因「门吃 `prompt.UserMessage` 而非 `message.Content`」归零；
当时唯一防线是 G29 **扫源码字面量**，挡不住等价回退。本轮补一条**行为级、端到端**的钉死。

- **harness（不改产品代码）** `eval/rover/r415/`：本地后端换成**确定性假实现**（模拟 llama-server 的
  `/health /props /apply-template /tokenize /completion`；待判原文含「谢谢」⇒ S 否则 P），
  链侧全真：真 `agenthost --frontend-api` + 真 DI 装配 + 真 `ModelQueueRouter` + 真 `LlamaCppLocalGenerationPort` + 真进程/HTTP（零 P/Invoke）。
- **判别力构造**：知识提示型技能 `skills/r415-gate-pin/SKILL.md`（`type: knowledge_hint`，关键词 `收到/谢谢`）
  命中后其 body 作为 `[技能知识参考]` 尾挂到 `prompt.UserMessage`（`IndustrialAgentV2.cs:1200`）
  ⇒ 该轮 `prompt.UserMessage != message.Content` ⇒ 门若吃错变量立刻可辨。
- **判据（预注册，全外部真值）**：A3 判别请求**不含**哨兵 + A7 远端请求**确实含**哨兵/参考块 —— 两者合起来才构成判别力；
  单看「判别请求含原文」没有判别力（`prompt.UserMessage` 本就包含原文）。
- **读数**：`verdict-r415.json = PASS`，**22 项断言 × 2 形态（JIT/AOT）全通过**。
  判别请求 3 次（文本 385/385/387 字符，哨兵 0 / 参考块 0 / 技能块 0）；远端正控 t2 哨兵 1 + 参考块 3、t3 哨兵 2 + 参考块 5；
  跳过轮回复 21 字（本地模板）≠ 桩罐头，P 轮 = 桩罐头 ⇒ 跳过真实、不静默、**假阴性 0**；
  负控臂 `off`（本地通道关）本地请求 0 / `/apply-template` 0，同一轮本就会走远端。
- **仪器教训（两次无效跑，已入档）**：① 假服务端必须显式解 `Transfer-Encoding: chunked`，否则请求体读成空
  ⇒ 判定恒 P、判据全废；② 判定规则必须锚定「待判原文」段（`【用户消息】` 到 `答案:`），
  全文匹配会命中判别提示词自带的 few-shot 示例（示例里就有 `收到，谢谢。 → S`）⇒ 三轮全判 S。
  两条都是**测量仪器缺陷**而非产品缺陷；无 A7 正控时，仪器错与「门吃错变量」无法区分。
- **边界**：假后端只证明**接线/机制**，不给任何自然分布比率（三轮不是分布）；增益本身仍以 R413 的真 r1 读数为准；
  微步骤/探索回注路径的追加块本轮未构造（仍只有源码级覆盖）；AOT 形态为**补充证据**（registry 口径：AOT 仅发布 tag 构成登记依据）。

## R414 — R371 断链真机验收（D7 优先）+ 失败可见性缺陷闭合：`Success=false` 的降级文案不再被链侧丢弃

**版本**: R414 · **日期**: 2026-09-14 · **状态**: 已实施（本地 commit，**未推**）
**主题**: backlog 最前未完成项 = R371 修复串的真机验收读数；验收过程抓到真缺陷并同轮闭合。

- **验收（真机 E2E，`eval/rover/r371d7/`，4 臂 24 项断言 ⇒ `verdict-r371d7.json = PASS`）**：真进程 `agenthost --frontend-api` + 确定性远端桩（逐请求落盘=外部真值）。
  - D7 截断续写：`llm_call_continue before=102 added=58 after=144 recovered=true`，`after` 与**独立复刻**合并长度逐位相同（overlap=16）；`tail_before` = 断点原文；救回后结构闭合。
  - D1 空正文恢复：`first_content_len=0 / first_reasoning_len=400 ⇒ recovered=true`。
  - **负控**：完整正文臂 ⇒ 远端 2 请求 / 恢复遥测 0（无病不治）。
- **★ 真缺陷（本轮抓到并修复）**: `src/agent/IndustrialAgentV2.cs:1604`（修复前）`if (!llmResponse.Success) response.Content = string.Empty;`
  ⇒ D1 在「重试后仍空」时写入的**面向用户降级文案被丢弃**，用户看到空白（真机 `empty_always` 轮 1 `reply_len=0`，`loop_turn.reply_chars=0`）。
  既有单测只在 **router 层**断言文案非空 ⇒ 链侧丢弃测不到（「有实现 ≠ 已接线」）。
- **落地（最小契约位，非布尔打补丁）**: `QueueResponse.ContentIsUserFacing` / `LLMResponse.ContentIsUserFacing`（默认 false = 零回归）+ `ModelQueueAdapter` 透传
  + 链侧 `UserFacingFailureContent(...)`裁定：**只透出被显式标记的内容**（未标记 ⇒ 仍为空，原始报错正文不外泄）+ `Success=false` 语义不变。
  可见降级文案不再拼接 `ex.Message`（内部信息卫生；原文保留在 `Error`）。
- **回归**: `UserFacingFailureTests` 5/5（含 2 条源级钉死）；修复后 4 臂重跑 `ok/empty/truncate` 读数逐位不变，仅 `empty_always` 轮 1 `reply_len 0→66`（修复前对照文件在库）。
- **口径澄清（审计须知）**: `llm_call.truncated` 反映**最终**正文闭合性（救回后为 false），截断事实只在 `llm_call_continue`；`added_len` = 续写原文长度（去重前）。
- **诚实边界**: 桩驱动 ⇒ 证明机制而非自然分布截断率；`empty_always` 为构造病态分布；单机单次读数。

## R413 — r1 本地真假判别接进链管道（端口化）：机械 Pass 前置 + 非 LLM 模板 ack ⇒ 一轮总 token ↓58.5% / 远端调用 ↓33.3%（判过）

**版本**: R413 · **日期**: 2026-09-14 · **状态**: 判过（C1–C4 全 PASS；本地 commit，**未推**）
**主题**: 用户钦定「利用 r1 对真假信息判别（挂载 role 额外数据，管道已接），让用户一轮任务总 token 显著下降 ≥30%（主要是不必要的 LLM API 请求少了）」。

- **落地（端口化，非硬接线）**: `ILocalGenerationPort`（`src/agent.modelqueue/LocalGenerationPort.cs`）+ `LlamaCppLocalGenerationPort`（`src/agent.llamacpp/`，进程 + HTTP，零 P/Invoke）；DI 接线 `ServiceCollectionExtensions.cs`；`ModelQueueRouter` 本地优先分支 —— 端口缺失 ⇒ 判据必拒 ⇒ **全走远端 = 零回归**；`TurnGateJudge`（机械前置门 + 结论区解析 + `ThinkOpen`/`ThinkClose` 常量）。
- **前置门 v2（本轮定，取代 v1 纯 r1 判别）**: ① 机械 Pass 前置（问号/疑问词、指令/新诉求、纠正/失败词、结构化实体、长文本 ⇒ **直接 Pass，不问 r1**）；② 仅无信号短消息交 r1（二元 S/P、192 token 上限、只读思考块之后的结论区）；③ 被跳过轮回复 = **非 LLM 模板**（`LocalSkipFallback`），不再让 r1 生成（v1 实测会复读前文并反问）。
- **判据读数（外部真值 = 桩侧逐请求落盘 + 驱动器观测；臂 A = 本地通道关 / 臂 B = 开）**:
  臂 A **12 调用 / 16,888 token**；臂 B **8 调用 / 7,007 token** ⇒ 调用 **-33.3%**、token **-58.5%**（阈值 30%）。
  门遥测（臂 B 7 轮到达推理段）：机械 Pass 3（轮1/3/5）+ r1 判别 4（轮2/4/6/8 全 Skip）；逐轮回复：轮2/4/6/8 = 模板（门消化），轮1/3/5 = 远端应答，轮7 = 链侧澄清拦截（两臂同现，与门无关）。
  **结算 `eval/rover/r413/verdict.py` → `verdict-r413.json`：C1 PASS · C2 PASS · C3 PASS（实质轮零误跳）· C4 PASS（跳过集恰好 = 预注册寒暄集、回复均为模板）⇒ 判过。**
- **前置门 v1（上轮）读数与换方案理由**: v1 达 -86.7% token / -50% 调用，**但判不通过** —— 负控抓 2 例误跳（新诉求「另外，测试命令呢？」、纠正语「不对，你上一条回答不准确…」）+ ack 退化 ⇒ 换「机械前置 + 模板 ack」。
- **本轮两处空心根因（真机诊断，均已修 + 已回归）**:
  ① **判的不是用户原文而是 `prompt.UserMessage`** —— 该字段已被 role 块/计划续跑/微提示追加（R379 Fix A）⇒ 机械门恒 Pass、增益归零；诊断法 = 先补 `local_turn_gate_config` 一次性遥测，把「门有没有开」变成可观测；修 = 判 `message.Content` + **G29 源级回归**（钉死链侧入参）。
  ② **源码写入通道把尖括号字面量替换成 tokenizer 形态**（思考块结束标记 → 码点 `0x3c,0xff5c,end,0x2581,of,0x2581,thinking,0xff5c,0x3e`）⇒ 解析器恒搜不到 = 空心降级（看着在判、全降级）；修 = 公开常量 `ThinkOpen`/`ThinkClose`（字符码构造）+ G24/G25 回归（含真机原文）。
- **机检**: `LocalTurnGateTests` **46/46**（含 G24 真机原文、G25 常量形态、G29 链侧入参源级钉死）；全量 **1158 / 0 / 0**（`TEST_EXIT=0`）。
- **AOT（发布形态验收）**: `dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_r413` ⇒ `PUBLISH_EXIT=0`、**IL 警告 0**、`agenthost` **15,138,848 B**（R412: 15,093,088 B）。
- **诚实边界**: ① 单轮脚本 / 单模型（r1-distill-1.5b-q4km）/ 单机单次读数，脚本参数化可重跑；② 机械信号表是**穷举白名单**，表未覆盖的短消息仍交 r1（本次 4 条寒暄全对，样本量小，**不构成 r1 可靠性证据**）；③ 桩侧逐轮归属受「后续轮 prompt 含历史文本」干扰 ⇒ 只作参考，判据只用外部计数 + 驱动器观测；④ 轮7 的 0 主调用是链侧澄清拦截、非门行为；⑤ 本轮改动**未推送**（推送暂停令在位）。
- **证据**: `eval/rover/r413/{verdict.py,verdict-r413.json,budget-A.json,budget-B.json,calls-A.jsonl,calls-B.jsonl,turns-B.jsonl,probe-struct.jsonl,run-B/data/telemetry/host.jsonl}`、`docs/plans/v0.35.0-r413-r1-local-verdict-token-budget.md`（§7.3–§7.6）。

---

## R403 — chat template 裁定：自研 Jinja 子集随 R408 退役 + 工具调用模板「无对象可验」（负控证明探针有判别力）

**版本**: R403 · **日期**: 2026-09-14 · **状态**: 关闭（裁定 + 待触发能力登记；**无代码改动**）
**主题**: backlog R403 的唯一待判项「工具调用模板是否改口径为验证 llama.cpp tool 模板行为」。

- **读数（两臂 + 判别力负控，一条命令 `python3 eval/rover/r403/probe_tool_template.py`）**:
  default 臂（GGUF 自带模板，`--jinja`）= `caps.supports_tools=false` / `caps.supports_tool_calls=false` /
  模板源 `tools` 变量 **0** 个 / `/apply-template` ±tools **逐字节相同**（md5 `b89299b3…`，24 B）/ completions ±tools
  `prompt_tokens` **4 → 4（Δ=0）**，HTTP 200 无报错；
  control 臂（合成 258 B 全 ASCII 模板，`--chat-template-file`）= `supports_tools=true` / ±tools **md5 不同**（29 B vs 62 B）/
  `prompt_tokens` **7 → 18（+11）** ⇒ **负控过关 = 探针有判别力**，default 的「相同」是真读数而非探针盲区。
- **排除替代解释**: `/apply-template` 在 control 臂读到 tools 并改变产物 ⇒ 端点确实转发 tools；default 臂的相同输出来自**模板**（无工具定义位），不是端点不支持 tools。
- **产品侧消费方**: `grep -rn -E 'tool_choice|ToolCall|tool_calls|"tools"' src/ --include=*.cs` ⇒ **0 命中**（零消费方）。
- **裁定**: **R403 关闭**。① 自研 Jinja 子集扩展的对象随 R408 退役（R409 已证渲染归引擎、调用方无法手拼）；② 工具调用模板**无对象可验**（引擎自报不支持 ∧ 模板零工具位 ∧ 产品零消费方，三方一致）。
  「工具调用」转**待触发能力**，准入判据三条**全绿**才开工：(a) `caps.supports_tools == true`；(b) 同 messages ±tools 的 `prompt_tokens` 有差（**不得只看 HTTP 200**）；(c) 产品侧存在发出 tools 的调用点。
- **诚实边界**: 仅现役模型 `r1-distill-qwen-1.5b-q4km` + 本机 build `b1-4df29be` 的单次读数；负控模板是**合成**的，只证探针判别力，不证任何真实模型支持工具调用；工具调用**出参解析**（`tool_calls` → OpenAI 格式）**未测**，属 (a) 之后的独立课题。
- **证据**: `eval/rover/r403/tool-template-behavior.json`、`eval/rover/r403/probe_tool_template.py`、`docs/reports/r403/chat-template-tool-scope.md`。
- **运行纪律入档（两次同族事故）**: ① 测量前清掉 6 个 R412/R413 遗留长驻 server（pid 230833/230849/232136/232152/233614/233632，RSS 合计 ≈3.5 GB，本机共 3.66 GB）⇒ `MemAvailable` 1.14 GB → 2.99 GB；
  ② `pgrep -f "[4]1999"` **仍自杀**（同一命令行的 `curl …:41999` 含裸端口号）——括号技巧只保护**模式字面量**，不保护同一命令行**别处**出现的目标串（同族：`ps | grep "[l]lama-server"` 被自己的 `echo "no llama-server running"` 命中）⇒ 正解 = 被测进程自落 pid，或同进程内 Popen + `killpg` 收尾。

## R412 — 多会话 slot 争用：单 slot 不踢缓存（三臂逐位相同）+ 会话级账本（分母不互相污染）

**版本**: R412 · **日期**: 2026-09-14 · **状态**: 已落地（代码/文档/登记见本次提交）
**主题**: R410 下轮候选 ②「多会话并发 slot 争用下的复用率」；R411 计划 §7 明确留 R412 的同一 regime。

- **先修前提（仪器校验）**: 冒烟阶段臂无判别力（两会话共享超长公共子序列 ⇒ A/B/C 读数相同）⇒ 改用**互不相同**的两份长文档前缀（`prefix-p1/p2.txt`，4336 / 4316 token），并用 `/apply-template` + `/tokenize` **独立量公共前缀**: LCP=0/1、最长公共片段 16 token ⇒ 有判别力。判据修订记录在计划文档 §2.1（**跑之前**写死，非跑后调参）。
- **服务端 regime 实测**（独立实现直连 HTTP，不经过产品代码；`-np 1`、`-c 4608 -b 512`、f32 KV、flash-attn off）: 三臂 A 同会话连续 / B 两会话交替 / C 真并发（线程同发）+ 第四臂 D（`-np 2 -c 9216`，每 slot 4608）⇒ 携带复用率**四臂逐位相同**（S1 0.9998 / S2 0.9991）；冷启 `prompt_ms` 148.3 s / 155.8 s vs 热轮 0.84 s ⇒ **真实 KV 命中**（非计数器假象）。⇒ **单 slot 不互相踢缓存**，K2b 双条件（≥97% ∧ ≥4224）在多会话形态下成立。
- **产品侧缺陷（代码事实钉死，与上面结论独立）**: `LlamaCppTextGenerator` 旧 ceiling 取**实例级** `LastPromptTokens/LastGeneratedTokens`，而长驻端口是进程内单例 ⇒ 多会话交替/并发时 A 读到的「上一轮」可能是 B 的 ⇒ 台账分母 `carryOverCeiling` 被污染（判红/判绿都可能失真且外部看不出）。修复 = 新增 `LocalSessionTracker`（按 `sessionKey` 分桶；无键退回实例级 = **零回归**）+ 端口暴露 `Sessions` 计数。
- **判据 J1a–J1h（含负控）**: 分桶（反例: 实例级会给 408）/ 首轮 0 / 无键兜底且不建桶 / 并发计数与租约归零 / **纯串行不得报争用**（`MaxConcurrentTurns==1 ∧ ConcurrentTurns==0`）/ 有界 / 夹紧 / 接线。单测 8 例。
- **诚实边界**: ① 仅 n=2 会话（同机单 server）；② `-np 1 -c 4608` 实测 server RSS **2.39 GB**（本机 3.66 GB）⇒ 更大 n 或更长前缀受内存约束，**未测**；③ 前缀中段截断点分布（R410 候选 ③）仍未测；④ 墙钟不作判据（只报单次形态）。
- **登记**: registry 新行 `llamacpp.session-ledger`（`updated_round=R412`）；TaskPlan 节点 `dev-multi-session-slot`；计划文档 `docs/plans/v0.34.0-r412-multi-session-slot-contention.md`；证据 `eval/rover/r412/`。
- **下轮候选（R413）**: ① **接产品链路**：本地生成（r1/llama.cpp 长驻端口）作为**链管道精炼计划节点**接入 `ModelQueueRouter` 通道选择（可替换执行面端口 + 数值对账 + 被使用计数 + 无设备负控）—— **与 R351 无关**（R351 只移除旧的「本地 LLM 使用」路径；用户 2026-09-14 纠正 R412 报告里的误读）；② N>2 会话与内存上限下的复用；③ 前缀中段截断点分布；④ 微内核 A/B（15× 悬案）；⑤ R402–R407 台账回填。

## R411 — 长驻生成端口 + 本地 K2b 台账：「口径必须靠独立实现对账钉死」+ 双条件判据

**版本**: R411 · **日期**: 2026-09-14 · **状态**: 已落地（代码/文档/登记见本次提交）

**用户令（逐字）**：「继续下一轮」

**完成记录**：
- **补上 R410 缺的第三条件**：新增长驻生成端口 `LlamaCppTextGenerator`（懒启动 + 单飞 + 跨调用保活同一 `llama-server`）。E2E（单进程 3 轮）逐轮 `ProcessStarts=1`，命中 **0 → 4352 → 4385**，携带复用率 **0.9998**，整体复用率 **0.9959**，前缀 **4337 ≥ 4224** ⇒ K2b 达标形态首次在产品侧复现（exit 0）。
- **负控（判据是活的）**：19 token 前缀会话 ⇒ 复用率 0.963、绝对长度不达标 ⇒ **判越线，exit 7**，诊断点名「前缀绝对长度 19 token（需 ≥4224）」；无 turns 的请求 ⇒ 用法错 **exit 2**（首跑曾是 core dump exit 134，已修）。
- **★ 口径教训（本轮最重要）**：按字段名把 `tokens_evaluated` 当成「新评估数」是错的 —— **它就是 prompt 总长**（`timings.prompt_n` 才是新评估数，`tokens_evaluated == prompt_n + cache_n`）。错算导致总长虚增（530 → 1042）、出现 **有效命中率 1.0302 > 1（物理不可能）** 与随后的假越线。独立实现（`/apply-template` + `/tokenize` + `/completion` 三方对账）把它钉死；**「比率 > 1」= 口径错的可机检特征**，已写成单测。
- **本地分母不套远端经验界**：远端 provider 的「需要命中的部分」含 64-token 单元打折（mt_fix4 规律），而 llama.cpp 的 KV 缓存连上一轮**生成**的 token 一起持有 ⇒ 本地台账用「可复用上限 = 上一轮总长 + 上一轮生成」，命中超出上限时**弃权**（记 `-1` + `Abstained`，不硬套判决）；命中未上报时**不判红**（缺失 ≠ 错误）。
- **判据 = 合取**：携带复用率 ≥97% **∧** 前缀绝对长度 ≥4224（沿用 R410「比值不是 KPI」）。单测 11 例（台账 7 + 口径 4，含「口径错 ⇒ 比率 > 1」与「比值达标/长度不足」两个负控分支）。
- **判据机检**：`eval/rover/r411/verify.py` **12/12 通过**；全量 **1087 / 0 / 0（34 s）**；登记表 **46 行**（新行 `llamacpp.session.long_lived_generation`）、TaskPlan **18 节点**、形式校验 **9/9**。
- **自错披露**：① 口径换算错（见上）；② 把 R410 的 780 字符前缀当成「4249 token」（4249 是探针运行时重复 25 次的产物）⇒ 首跑正负例结论颠倒；③ 预注册判据 N1 写错（预言「比值达标」，实测比值也不达标），**修正判据并另立单测覆盖该分支**，不为让脚本变绿而放宽；④ 会话分支曾在 `try` 之外 ⇒ 异常逃逸 core dump；⑤ STJ 默认大小写敏感 ⇒ 小写 `turns` 反序列化成空。

**诚实边界**：单 slot 顺序两会话、只测 497/4337 两点、3 轮 n=1 形态；多会话并发争用未测；**产品主链路未接**（`ModelQueueAdapter` 仍走远端）；正例前缀是合成重复文本（4337 token），真实 system/skills 前缀能否天然 ≥4224 未验证；助手轮回放的逐字节一致性未单独取证（本轮复用近全量，但无字节级对照）；墙钟不作判据。

---

## R410 — 会话长前缀复用（K2b 落点）：「比值不是 KPI」+ 宿主生命周期缺口 + 生成口径分离

**版本**: R410 · **日期**: 2026-09-14 · **状态**: 已落地（代码 `8263ac8`；文档/登记见本提交）

**用户令（逐字）**：「继续下轮」

**完成记录**：
- **实测（判据先预注册）**：同一 server 内，4255 token 长前缀第二次请求只重算 **5 token**（`cache_n=4250`，复用率 **0.9988 ≥ 0.97**，墙钟 233.9 s → 0.5 s）；负控（前缀首 token 改变）归零；`cache_prompt=false` 恒 0。
- **关键结论：比值不是 KPI，绝对长度才是** —— 短独立 prompt 的「复用比」0.94 看似不低，但绝对可复用只有 **17 token** ⇒ 对 K2b 红线（≥4224）覆盖 **0.402%**，结构上不可能达标。只看比值会得出相反结论。
- **宿主生命周期缺口（实测，非推断）**：同样 `--reuse on` + 稳定 487 token 前缀，两次 CLI 调用 `CachedTokens` **都是 0**、`SessionCacheMisses=1` —— 每次调用新起 server（新 KV 缓存）⇒ 跨进程复用 **0%**。⇒ **K2b 达标三条件：长驻 server + 稳定长前缀 + cache 开；缺「长驻」时另两条都白搭**。
- **代码**：`CompletionReuse {Session, Reconciliation}`（`GenerateAsync` 默认 Session = 生产口径）；`CompletionProfiles.Build()` 收敛为「口径 → 参数」唯一映射点；`CompletionResult.CachedTokens`（服务端 `cache_n`，非估算）；`SessionReuseCalls`/`ReconciliationCalls`/`SessionCacheMisses`（静默失效可见化）；CLI 新增 `--reuse on|off` 与 `--system-file`（会话长前缀入口）。
- **测试**：新增 `CompletionReuseTests` **4/4**；全量 **1076 / 0 / 0**（R409 基线 1072 + 4）。
- **顺带修掉两个真缺陷**（均由全量回归暴露、非本轮引入，同属「拿墙钟当闸门」类）：① `SessionPerformanceTests` 的墙钟 3x 比值断言 ⇒ 改为「等价性作判据、计时只作信息」；② `LlmServiceStatusTests` 的 5 s 固定就绪截止 ⇒ 放宽到 30 s 并把实测等待写进失败信息。两者在争用下都产生假红（单独复跑全绿）。
- **登记**：`docs/verification-registry.json` 新行 `llamacpp.session.prefix_reuse`（L4，45 行，`updated_round=R410`）；TaskPlan 节点 `dev-session-prefix-reuse`；计划文档 `docs/plans/v0.32.0-r410-session-prefix-reuse.md`；证据 `eval/rover/r410/`。

**自错披露**：① 探针 v1 成本估小（单线程 prefill 实测 26 t/s ⇒ 4807 token 一遍 185 s）且只在末尾落盘 ⇒ 被掐断后零证据，v2 才改成分臂增量落盘；② 「会话内复用 99.88%」与「跨进程复用 0%」两条曾混在同一结论里，补跑 CLI 后才分清。

**基线**：全量 1076/0/0；本地生成 17.9 t/s（llama.cpp 不变）；K2b 会话内顺序复用 **0.9988**（达标）/ 跨进程 **0**（缺口）。

**下轮候选（R411）**：① 产品侧长驻 provider 接线（嵌入侧已是 `AddSingleton`，生成侧待接）；② 多会话并发 slot 争用下的复用率；③ 前缀中段变化的截断点分布；④ 微内核 A/B（15× 悬案）；⑤ R402–R407 台账回填。

## R409 — 本地 prompt 模板闸门（结构性阻断手拼）+「权威 prompt」BOS 口径修正

**版本**: R409 · **日期**: 2026-09-14 · **状态**: 已落地（工作区，待 commit）

**用户令（逐字）**：「继续下轮」

**完成记录**：
- **实测（判据先预注册，后改代码）**：模板来源对账 —— GGUF 内嵌 jinja（走 `POST /apply-template`）与归档 `eval/rover/tokref/r1_chat_template.jinja` 在 **3/3 消息形状逐字节一致**（diff 0 B）⇒ K2b 模板来源漂移风险关闭。
- **BOS 归属裁决（真缺陷）**：96 B 字面权串 + 默认 tokenization（`add_special=true`）= **18 token / 双 BOS**；规范形式 = 渲染串（67 B）+ tokenizer 自动 BOS = **17 token / 单 BOS**，两者 token 流等价（`IdsEquivalent=true`）。产品通路实测：`literal` 18 vs `chat_template` 17，**生成 24 id 逐位相同** ⇒ R408 对账结论不受影响；双 BOS 的实际代价是 **+1 prompt token** 与**两通路前缀不可复用**（K2/K2b）。
- **闸门落地**：新端口 `ILocalPromptRenderer`（唯一实现经 `/apply-template` 由**模型元数据**渲染 ⇒ 调用方物理上无法手拼）；`LocalPromptGate` 四规则（来源非模型元数据 / 空产物 / 字面含 BOS / 以 EOS 结尾 ⇒ 全判红）；`GenerateAsync` 只收结构化 messages；字面通路降级为 `CompleteLiteralPromptAsync`（显式诊断用 + 计数）；被使用计数 `TemplateRenders` / `PromptGateRejections`。
- **规则按实测修正**：初版「不得包含 EOS」会**误拦合法多轮**（118 B 含 EOS 轮分隔符、不以 EOS 结尾）⇒ 改为「不得以 EOS 结尾」。
- **机器验证**：`agenthost --llamacpp --verify-template`（退出码 6 = 未通过）⇒ `Verdict=gated_single_bos`、`RenderedBosCount=1`、`LiteralBosCount=2`、`IdsEquivalent=true`、exit 0。
- **测试**：新增 `LlamaCppPromptGateTests` **9/9**（sha 锚点钉死 + 5 项注入缺陷负控 + 2 项防误拦反向控制）；全量回归 **1072/0/0**。
- **AOT**：规范命令复跑 **exit 0 / 0 IL 警告 / 14,950,608 B**（政策 `release_tag_only` ⇒ 仅参考证据）。
- **登记**：`docs/verification-registry.json` +`llamacpp.prompt.template_gate`（L4，44 行）；TaskPlan 节点 `dev-local-prompt-template-gate`；计划 `docs/plans/v0.31.0-r409-local-prompt-template-gate.md`；证据 `eval/rover/r409/`。

**自错披露（3 处）**：① 首轮把 `2081`（字符）与 `2237`（UTF-8 字节）当成两个模板的长度，误报「差 156 B」（单位错）；② 闸门初版 EOS 规则会误拦合法多轮输入；③ R409 探针脚本内建裁决行问错对象（比较了 `96B/add_special=true`）故打印 False —— 正确等价对由 `--verify-template` 独立确认。

**基线**：R408 全量 1063/0 ⇒ R409 全量 **1072/0/0**；本地生成 17.9 t/s（llama.cpp，与 R408 持平）。
**台账缺口（遗留）**：R402–R407 未回填本台账，其证据在 `eval/rover/r40x/` 与 `docs/plans/v0.2x-r40x-*.md`。

## R408 — 本地 GGUF 引擎整线退役，产品线全面切 llama.cpp（进程 + HTTP，零 P/Invoke）

**版本**: R408 · **日期**: 2026-09-14 · **状态**: 已落地（commit `b00917c`，本地未推）

**用户令（逐字）**：「去掉所有关于gguf的本地代码开发，完全改用llama.cpp」+「不用对比自研的了，直接用llama」

**完成记录**：
- **退役范围**：`src/agent.rover/{gguf,quant,infer,runtime,token,cli}/` + `src/agent.embedcpu/` 整工程删除（10.3k+0.6k LOC）；`formal/` + `gpu/spirv/` 保留（非 GGUF 内核）；`agent.rover` 不再产出可执行文件。
- **接入形态**：`src/agent.llamacpp/`（Host / Client / Provider / TextEmbedder）只走「进程 + HTTP」，全仓 `DllImport`/`LibraryImport` **0 命中**。依据：跨平台（Windows 无 `AddressFamily.Unix`）+ R90 实测 LLamaSharp native interop 在 NativeAOT 下 SIGSEGV。
- **两进程形态**：生成与嵌入互斥（`/v1/embeddings` 需 `--embeddings` 启动）。
- **读数**：生成 24/24 token id 与 llama-cli 基线逐位相同（dev 17.891 / AOT 17.64 t/s，`IdsMatch=true`）；嵌入 768 维 L2 归一，命令路径与 DI 路径指纹一致（`sha256=d5336321…`），新旧向量 `cos=0.1586`。全量回归 **1063/0/0**；AOT 0 IL 警告。
- **登记表**：3 行引擎对账行改写为 `llamacpp.process.boundary` / `llamacpp.embedding.port` / `engine.retired.no_local_gguf`。
- 口径修正（R409 追认）：R408 所用「96 B 权威 prompt」字面含 BOS，在默认 tokenization 下会双 BOS（18 token）；规范形式为渲染串 + 自动 BOS（17 token）。生成结果 24/24 不受影响。

**基线**：退役前 1130/2/1132 ⇒ 退役后 **1063/0/0**。

## R401 — 能力自检循环常驻化（用户令：R400 后一直执行 + 60 分钟检测机制）

**版本**: R401 · **日期**: 2026-09-14 · **状态**: 已落地（常驻）

**用户令（逐字）**：「我发现你再R399后就没有遵照之前的安排 继续 进行 【参照当前上下文（非本agent项目的) 并使用本agent和py开发随机程序和解开随机数学难题用于本agent能力自检和总结通用性skill放入skills文件夹内】 这轮R400结束后 请一直执行该任务 （全部任务完成后再次执行，需要检测机制）」

**完成记录**：
- **循环本体** `scripts/capability_cycle.py`（853 行，stdlib）：`status`（检测机制入口，判 `tasks|selfcheck`）/ `emit`（按 seed 生成一轮随机题：6 程序家族 + 8 数学家族）/ `grade`（机械判定：数学=独立暴力 oracle；程序=隐藏用例族 + 失败分类）/ `selftest`（判定力负控）。
- **检测机制**：cron `10f9d6454575` 每 60 分钟跑 `status` ⇒ `tasks` 推进最前计划项一步；`selfcheck` 跑随机程序+数学题自检并沉淀通用性 skill。
- **判定器自检实测 SOUND**：参考解全绿（merge_intervals 16/16、roman_canonical 27/27、ttl_cache 4/4、数学 8 家族 19/19 与暴力 oracle 一致）；**8 个变异解全部必红**且红在预期判据上。
- **本轮真跑（cycle-20260914-s20260914）**：数学=生成树计数 **21**（矩阵树定理 ≡ C(8,5) 子集枚举 ≡ 判定器 oracle，三方一致）；程序=TtlCache **4/4**。读数落 `eval/capability/kpi.jsonl`。
- **通用性 skill**：`skills/spec-uniqueness-and-judge-soundness/SKILL.md`（type=knowledge_hint）—— 判据口径唯一化 + 判定器自检（参考解/变异解/反例成族/场景参数泛化）；过 `SkillGeneralizationTests`（全目录遍历）10/10 + 产品侧 `SkillPackageLoader` 4/4。

**本轮由自检抓出的真缺陷（3 处，全部已修并固化进 skill）**：
1. 「严格解码」写成「贪心消费恰好耗尽」—— **不充分**（非规范写法同样耗尽）⇒ 参考解与题面自相矛盾；改为互逆判据。
2. LRU「最近使用」用 `now` 值当次序 —— 时间戳相等时次序不确定 ⇒ 正确解不唯一；改为访问先后序号（内部自增），并用「时间戳全相等」用例逼出该语义。
3. 判定场景把 `capacity=2` 写死且该判定面无参考解 ⇒ 缺陷躲过自检；改为参数泛化生成 + 每个判定面都有参考解覆盖。

**基线**：R400 全量回归 1088/1088；本轮新增 0 条 C# 测试（循环本体为 py 侧自检设施），门禁 10/10 + 4/4。

## R398 — 随机化能力自检探针 + 通用性 skill 沉淀（exp14 长期线首轮）

**日期**: 2026-09-13 · **状态**: 完成（M1–M5 落地；M6 题集加硬列下轮）· **计划**: `docs/plans/v0.24.0-exp14-random-probe-selfcheck.md`

**用户令（逐字）**: 「使用本agent和py开发随机程序和解开随机数学难题用于本agent能力自检和总结通用性skill放入skills文件夹内」（长期任务，须纳入文档）。

**完成**:
- **随机题集生成器** `eval/probe/tasks.py`（627 行）：程序 6 族（括号修复/矩阵螺旋/最大子段/区间和/CSV 聚合/去重计数）+ 数学 5 族（组合取模/行列式取模/二次剩余解数/期望值/最长递增子列）；每题**双路径验算**，两条独立路径不一致 ⇒ **拒绝发题**。
- **判定器** `eval/probe/grade.py`（300 行）：隔离目录 + 超时 + `-I -B` 沙箱执行；**只认隐藏用例**；失败模式分类；**判定器自身反向负控**（比对函数打坏后必须转红）。
- **编排器 + 真机适配器** `eval/probe/run_probe.py`（380 行）：`oracle` / `file:` / `command:` / `agent`（真机走 AOT `agenthost -q`，py 插件落盘产物）；回复原文落档 `data/probe/replies/`。
- **真机自检跑通**：6 题 21 用例 **21/21 = 1.0000（73.33s）**，失败模式 `{ok:21}`，6 族全 1.0。
- **经验抽象 → skill**：`skills/independent-verification-before-claim/SKILL.md`（语言无关，`type: knowledge_hint`）。
- **门禁扩面**：`SkillGeneralizationTests` 从"只体检 1 个 skill"改为**遍历全部 `knowledge_hint` skill**（加载 / keywords+regex_patterns 非空 / 正文零语言特性 / 负控），当场暴露 2 处存量裂缝并修复：`image-gen` 零 `regex_patterns`（匹配器永不触发）、`critic-rules` 正文含语言 token（语言映射外置到 `references/lang-mapping.md`）。

**关键因果链（判定口径）**: 真机首轮 p001 报 `no_code`（0/6）→ 查回复原文发现 agent **已产出正确程序**（`py_57906c9279782c29.py`，`py_compile` ✓、run exit=0），根因是判定器只认围栏代码块，而产品真实交付 = **CLI 回复区裸代码 + 落盘产物** → 改为多路候选 + 取最长可编译前缀 → 同一回复重判 **6/6**。教训：**判定口径假设错 = 反向的空心指标**（会把满分记成 0 分）。

**负控总数**: 生成器 21/21 + 判定器 13/13 + 编排器 11/11，全部含"打坏判据必须转红"的反向控制。

**诚实边界**: ① 样本 6 题且 100% ⇒ **饱和、零区分度**，对能力提升不敏感，M6 必须加硬；② 数学只判最终答案，不判推理链；③ 沙箱**不是安全边界**（不禁网）；④ 单次读数含模型侧波动，须同题成对比较。

## R397 — DCR 单一口径重算(FAVA 语义) + 口径敏感度实测量化(30.34pp)

**用户令**: 续轮（"继续下轮"）· 承接 R396 附带解锁的 FAVA 正文取证。

**因果链**: R388 起本仓 DCR **双口径并列**(弃权计合规 **145/145=100.00%** / 保守 **101/145=69.66%**), "是否达到 90.5%±5pp"因此**不可断言** —— 100% 与 69.66% 分落区间上/下, 达标与否"完全取决于弃权是否计合规"。R396 把 FAVA 正文里的口径取到 (公式/无弃权项/fail-closed/单一二元矩阵) ⇒ 阻塞解除, 但**按该单一口径重算未做** ⇒ 本轮即补这一刀。

**完成记录**:
- **口径定稿**: `DCR = (TP+TN)/(TP+TN+FP+FN)`, **无弃权项**, 非 `Proceed` 一律 **fail-closed 记 block**(期望侧 `Proceed` ⇒ allow, 其余 ⇒ block; 实际侧同理)。
- **单一口径结果**: **DCR = 145/145 = 100.00%**; 混淆矩阵 **TP=94 · TN=51 · FP=0 · FN=0**; 六类 category 逐类 DCR 全 1.0000。
- **口径敏感度实测(本轮关键产出)**: 同一份数据三种读法 —— fail-closed **100.00%** / 仅可决断集(101 条) **100.00%** / 弃权与畸形按放行 **69.66%** ⇒ **跨度 30.34 pp**。⇒ **"±5pp 裕度"此前不成立的根因是口径自由度本身(30.34pp ≫ 5pp), 不是测量噪声**; 口径现已钉死, 该自由度消除。
- **跨实现交叉对账 4/4**: 单一口径重算器只从 C# 侧报表(`scripts/kpi_dcr.py` 产出)**独立计数**抽数对账 —— `N=145` ✓ / `Proceed == TN == 51` ✓ / `可决断集 == Proceed+Violation == 101` ✓ / `弃权+畸形 == N−可决断 == 44` ✓(符合"跨实现对账换独立实现"铁律, 不 import 内核代码)。
- **负控 7/7**(`dcr_align.py --selftest`): 含**解析 oracle**(400 次洗牌 DCR 均值 ≈ `(51²+94²)/145² = 0.5440`)、单点翻转 **Δ=1/145**、常量分类器基线(**全 allow 35.17% / 全 block 64.83%**)⇒ 100% 的信息量全在"同时拿到 51 allow + 94 block"。
- **自捕 2 缺陷(已修)**: ① 自检计数写死 `6` 而实际 7 条 ⇒ 恒 rc=1("闸门自己恒假"的镜像缺陷); ② 敏感度表混用原始处置与二元值 ⇒ 崩(均被一轮 selftest 抓出)。
- **文档收口(禁再"双口径并列")**: 本节 + `eval/dcr/README.md`(口径定稿注 + 清单加 `dcr_align.py`)、`docs/verification-registry.json`(`dcr.harness` 行)、`docs/plans/v0.23.0-exp12-*`(§S4 / §口径纪律)、R388 诚实边界段均改为**单一口径 + 敏感性**。
- 机读产物 `docs/reports/dcr/dcr-single-metric.json`; 报告 `docs/reports/r397/r397-dcr-single-metric-recompute.md`。

**诚实边界**: ① **题集饱和** —— 145/145、FP=FN=0 ⇒ 该数字对能力提升**零灵敏度**, 加硬用例(长轨迹/语义降层)是"达标断言"的唯一前置; ② **与 FAVA 90.5% 不可比**(801 例 aggregate × 三基准 × 含自然语言→IR 降层损失, 本仓 145 例受限片段、零 LLM、无降层)⇒ **"DCR=100%"≠"达到 90.5%±5pp"**; ③ 标签独立性有限(62/145 构造定义; 83/145 z3 推导, 但 z3 与内核共享整数语义 ⇒ 共同盲区不可自发现); ④ 口径映射是本轮工程裁定(可审可改, 改则数字变)。

**基线**: 纯 Python + 文档轮 ⇒ **零 C# 改动**; 全量测试基线不变。

---

## R396 — 产品侧 Vulkan 端口(去 Silk.NET 依赖, 名字/版本与 Silk.NET 逐字一致)

**用户令 (逐字)**: "不要引入silk.net; 但用的vulkan.dll文件名与版本请和silk.net库一致。"

**因果链**: 上轮遗留"产品侧进程内选 vulkan 需引 Silk.NET ⇒ 6 条第三方 IL 告警 ⇒ 待用户决策"; 本轮裁决 = **要能力不要依赖** ——
Vulkan 只需 BCL 的 `NativeLibrary` + 函数指针即可自载, 第三方绑定并非必需; 但"自载"必须证明**与 Silk.NET 用的是同一个加载器**,
否则就是另一套东西 (名字/soname/请求版本任一处不同 ⇒ 行为可能分叉)。

**落地**: 新增 `src/agent.gpu` (零外部包依赖 / 零反射 / AOT)。名字与版本**取证自包内程序集**, 不是读文档:
`eval/vulkan/extract_silknet_loader_names.py` 机械提取 UTF-16 字面量 → oracle (`vulkan-1.dll` / `libvulkan.so.1` / `libvulkan.so` / `libvulkan.dylib`, 源 sha256 落档);
请求版本与引擎侧 Silk.NET 路径 (`Vk.MakeVersion(1,1,0)`) 源码级锁定。

**真机证据**:
- 机检 **5/5** (`VulkanLoaderParityTests`): 名字逐字对账 + sha256 溯源 + 版本反漂移 + **依赖声明投影检查**(不引 Silk.NET: 注释不算、声明算) + 负控 + 真机设备 + 池化复用。
- **JIT 与 AOT 同一结论**: AOT 单文件 1.19 MB, **IL 警告 0**, 输出目录无任何托管依赖; `probe` 输出 `vkdevice{name="llvmpipe (LLVM 20.1.2, 256 bits)" api=1.4.318 vendor=0x10005 type=cpu}`。
- **跨实现对账 SOUND**: 与系统 `vulkaninfo` 逐字段比对 **6/6 一致** (设备名/apiVersion/driverVersion/vendorID/deviceID/deviceType), 对 AOT 产物复跑仍 SOUND ⇒ 自写绑定与独立实现等价。
- 负控 `probe --negctl` ⇒ `not_found` 显式失败 (不静默回退 CPU)。

**诚实边界**: ① 本轮只打通"加载器/实例/设备枚举"(Stage 1+2), **产品侧计算管线 (descriptor/pipeline/命令缓冲) 仍是引擎侧实现**, Stage 3 待做; ② 内存堆解析 (结构对齐) 未做, 只断言对账过的字段; ③ 本机唯一设备是 **lavapipe 软件 ICD** (显示设备为 QEMU 模拟 Cirrus GD 5446), **真 GPU 斜率需外部机器**, 复跑脚本已备; ④ oracle 溯源依赖本机 nuget 缓存, 缺失时显式 warn 而非静默。

**报告**: `docs/reports/r396/r396-product-side-vulkan-loader-parity.md`。

**附带解锁 (⑤ dcr-align)**: FAVA 正文 (arXiv `2607.27267v1`) 已抓到并落盘, DCR 口径取得权威原文 ——
`DCR = (TP+TN)/(TP+TN+FP+FN)`, **无"弃权"项**, 不确定一律 **fail-closed 记 block**; aggregate = **单一二元矩阵**(非各集宏平均);
trace-conditioned 100.0% 论文自陈为 *labeled diagnostic*, 须与 zero-shot 主表分开读; 论文**未给方差/置信区间** ⇒ ±5pp 仍是本仓自设工程裕度。
由此解释本仓"合规 100.00% / 保守 69.66%"两面不矛盾(弃权处置不同); 对齐重算(=fail-closed 归并后单一口径)**已于 R397 完成**(见 R397 节): 单一口径 **145/145 = 100.00%**, 且**口径敏感度实测 30.34pp** ⇒ ±5pp 不够用的根因是**口径自由度本身**。
取证件: `docs/reports/dcr/dcr-align-fava-source-2026-09-13.md`。

---

## R395 — BGE 闸门真修 + 停 cron + 融合线实测(RRF 可达值 0.8500)

**用户令 (逐字)**: "修完闸门 停 cron 走融合线"; 前置问 **"先告诉我一个结论, bge底座是否还需要自己二次训练, 有意义么, 提升性能代价多大?"**

**结论**: **不需要**。融合线(0 训练 / 0 新模型)真值: r@1 **0.5333** / r@10 **0.8500** / mrr@10 **0.6439**, 比最优单路(词法 0.7500) **+9.83pt**(网格最优; RRF 默认 k0=60 读数为 **0.8000**, +5pt), 比训练线最优(v11 r@10 0.6667) **+18.3pt**。

**因果链**: 训练线 9 轮 0 采纳的真因不是"数据还不够", 而是**收益天花板被零成本基线压住** —— 加数据到 1112 对后 r@10 只到 0.6667, 仍低于词法 bigram(0.7500)与 bge-base 底座(0.7417); 而互补性实测显示**词法 × dense-base 的并集口径已达 0.8667** ⇒ 真正有增量的是**融合**, 不是**训练**。

**两个真缺陷修复 (用户点名"修完闸门")**
| 缺陷 | 原状 | 现装 |
|---|---|---|
| G3 **口径分叉** | 文档 §5「延迟≤15% ∧ RSS≤15%」vs 代码「算力占比<5%」, 且代码从未测过真实耗时 | 三子判据同阈值实装: **算力≤5% ∧ 延迟≤15% ∧ 内存≤15%**; 延迟分母 = **绕缓存实测真前向**; 内存为**静态代理**(口径明写, 不得称 RSS 实测) |
| G5 **空心闸门** | 代码即 `g["G5"] = True` —— 确定性从未被检查, 却每轮记"G5 通过" | 真跑 4 条逐位判据: ①encode 重复性 ②顺序无关 ③秩可复现(与择优记录秩逐位比较) ④扰动负控 |

**真机证据**
- 闸门 A/B (同 1112 对 / 同算法 / 仅判定代码变): v11 `G1✓ G2✓ G3✓ G4✗ G5✓` ⇒ rolled_back; 指标 **与 v10 逐位相同**(0.3167/0.6667/0.4183) ⇒ **改判定不改结论, 只让结论变真**; G3 明细 `fwd_ms_per_vec 96.304 / lat_ratio 0.0109 / mem_ratio 0.00566`。
- 融合判据全绿: ①自建排秩与 `L.lexical_baseline` **逐位一致** + dense 两路与冻结节账(small 0.6333/base 0.7417)一致; ②单调变换后融合**逐位不变**, 负控改 120/120 条排秩; ③秩单调 fuzz 300 例; ④随机路 0.375 / 洗牌 0.0083(≈随机水平 0.0077)。
- 机检新增: `eval/bge/test_gates.py`(文档↔代码同阈值防漂移 + G3 两侧样例)、`eval/bge/test_fusion.py`(手算 RRF oracle + 三种可判别负控 + 边界口径)。

**停 cron**: 作业 `bge-idle-train(静默)` 已 pause(`enabled:false`, 停于 2026-09-13 21:49:48, 末次 v10), **未删除**可 resume; 停前 v10/v11 恰为该线最佳读数 ⇒ 属"见顶转线"而非止损。

**诚实边界**: ① 评测集仅 120 条(1 条=0.83pt), 主张取保守值 +5pt/+9.83pt 并列; ② 0.8500 为 36 格网格在**同一评测集**选优 ⇒ 选择性偏差已披露, 推荐读数 0.8000(k0=60); ③ 融合**产品侧端口未实现**(仅脚本级实测); ④ G3 内存子判据是静态代理; ⑤ 训练线唯一翻盘前提 = 接真实检索标注(属领域微调, 本机不支持 T2/T3)。

**教训归档 (通用化, Id/Pattern 无语言专名)**: 10.6 `gate.literal-true-is-hollow` / 10.7 `instrument.resolution-boundary` / 10.8 `control.injection-must-alter-observable` / 10.9 `assertion.must-be-provable`(见 `docs/plans/v0.22.0-exp5-lesson-table.md` §10.6–10.9)。

**报告**: `docs/reports/r395/r395-bge-gate-fix-fusion-and-cron-stop.md`; 融合报告(脚本自写, 禁手抄) `docs/reports/bge/fusion-2026-09-13.md`。

---

## R394 — prompt 缓存命中率红线 95% → 97%(口径权威单点变更 + 结构性归因机检)

**用户令 (逐字)**: "token命中率红线报警改为97%"。

**因果链**: 红线是**首要 KPI 的判定权威**, 其成立依赖两点: ①**单点权威** —— 阈值只有一个来源 (`PromptCacheRedline.Threshold`), Python `scripts/kpi_cache_hit.py` 的 `REDLINE` 与之机检锁死, 其它文件里的字节级代理断言必须**从常量派生**; ②**阈值 ⟺ 结构必需项** —— 阈值提高必须同步改"加厚前缀"的定量依据 (97% ⇒ 前缀 ≥4224 token 最坏对齐稳健界 / ≥2176 对齐最优)。

**本轮真缺陷修复**: 两处机检 (`SessionInjectionPlannerTests` 等) 仍带 **R380 之前的陈旧 90% 标签** —— 属"字节级代理断言", 改常量它照旧绿 (判定空心) ⇒ 改为**从权威常量派生**。

**顺带更正陈年口径残留**: 文档原写"红线等价于每轮增量 ≤ 前缀/9" (90% 旧口径 `hit/(hit+miss)`, 增量进分母)。**R380 口径依 `min(本轮,上轮)` 后增量与判定无关**: 有效命中率 = 命中上限/上轮前缀 = `1 − (64+r)/P`; 只有 prompt **收缩**才换分母。

**真机证据** (`docs/reports/r385/r394-cache-redline-97.md`):
- 聚焦 19/19 Passed (`Threshold = 0.97`)；全量 **1060/1060 Passed (33 s)**。
- 新阈值下真遥测: 轮2 **0.9574** / 轮3 **0.9543** / 按会话 0.9311~0.9689 —— **全部越线** (旧口径下"看着达标")。
- **结构性归因机检: 6/6 实测命中 == 结构上限 `(⌊P/64⌋−1)×64` ∧ 缺口 == 单元对齐损耗 `64+P%64`** ⇒ 越线 100% 归因**前缀厚度不足**, 装配侧缺陷 **0 例**。

**诚实边界**: 97% 在现前缀 (≈0.98k–2.55k token) 下**结构性不可达**(P=2551 上限仅 0.9533, 已吃满); 达标需前缀 ≥4224 token ⇒ 与"降低 tokens"存在张力, 留作用户裁定 (报告 §5 给出 A/B/C 三选项)。

## R393 — 本地 BGE 接入 Vulkan GPU 执行端口(端口化 + 真机对账 + 驱动约束取证)

**用户令 (逐字)**: "agent 本地bge也需要加vulkan gpu运行端口"。

**因果链**: 本地 BGE 一次嵌入的热点是**每层 6 次矩阵乘**(q/k/v/attn_output/ffn_up/ffn_down ⇒ 24 次 [seq,in]×[in,out])。若把"GPU 版"写成第二个前向, 立刻产生**两份前向语义**(LayerNorm/注意力/GELU/池化任一侧改动都要双改双测) —— 这是教训表 §10.2(同构多表示的形状静默错)的同类风险。故落点是**端口 + 单一前向**: 端口契约 `IMatMulBackend`(`src/agent.embedcpu/MatMulBackend.cs`), CPU 实现 `CpuMatMulBackend`(SIMD), Vulkan 实现 `src/agent.rover/gpu/VulkanMatMulBackend.cs`, 新建形状特化内核 `Kernels.MatMulBias(inDim,outDim)`, 前向本身**一行没多写**(只把 6 个投影改走端口)。

**交付**:
1. **端口契约与实现**: `MatMulBackend.cs`(新, 端口 + CPU 实现, 声明"纯函数 + 长度恰为 seq*outDim + 舍入语义"); `BgeCpuEmbedder(model, IMatMulBackend?)` 构造注入(**缺省 CPU, 行为与旧版逐位一致**), 新属性 `MatMulBackendName` 供证据; 删除私有 `MatMulAdd`(原样搬进 `CpuMatMulBackend`)。
2. **Vulkan 端口**: `VulkanMatMulBackend`(端口名 `vulkan`, 形状特化内核缓存, 三个形状断言 weight/input/bias, 暴露 `Dispatches`/`LastDispatchMs`/`PoolStats`); `agent.rover` 单向引用 `agent.embedcpu`(无环)。产品程序集**不引入 Silk.NET**(沿用 `agent.csproj` 既有边界)。
3. **内核**: `Kernels.MatMulBias` 4 绑定 (0=W 1=X 2=B 3=Y), `inDim/outDim` = 编译期常量(形状特化 ⇒ 内核内不用 ArrayLength 反推维度), 越界守卫 `i ≥ ArrayLength(Y)`; `Spv` 新增 `OpULessThan=176`/`OpUDiv=134`/`OpLoopMerge=246`/`ScFunction=7` + `LoopMerge()`/`FnVar()`(函数首块钩子 `Build(..., firstBlock)`), 全部经 `SpvRegistryAudit` 对权威 grammar 机检(新增 `ScFunction` 别名绑定, 否则审计红 —— 本轮真红过一次)。
4. **真机入口**: `agent.rover embed [--backend cpu|vulkan] [--device I] [--repeat R] [--text T] [--compare] [--selftest]` —— 输出全机器可读行(`bgemodel/port/vkdevice/membase/emb/determinism/parity/portcheck/pool/mem/done`), 零 shell / 零 Console 直写。

**真机证据**(`docs/reports/r385/r393-bge-vulkan-port.md`, 原始日志 `/tmp/r393/`):
- **端口确实被使用(防空心)**: `portcheck{dispatch_calls=expected}` 在 72 / 216 / 864 三种规模下 `match=True`(期望 = 层 4 × 6 × 文本 3 × 重复 R)。
- **数值对账**: Vulkan vs CPU `max_abs_diff ≤ 2.538E-007`, `cos=1.000000000`, `verdict=PASS`; CPU 档 `max_abs_diff=0.000E+000`(逐位相同)。舍入语义已写清: 内核**顺序**累加 vs CPU `TensorPrimitives.Dot`(**SIMD 多累加器**) ⇒ 不逐位相同, 故判据 = `≤1e-3 ∧ cos≥0.99999`(把"逐位一致"当判据会假红)。
- **确定性**: `repeat=3` 三个 pass `identical=true`(逐位)。
- **负控**: `--device 99` ⇒ `vkerr{note=device_index_out_of_range}` + `done{ok=false reason=device_unavailable}` 退出码 1, **不产出任何嵌入**(不静默退回 CPU)。
- **AOT**: 引擎侧 `IL_warnings=6`(全部第三方 `Silk.NET.Core.Loader` IL3000/IL3002) 且**原生二进制真跑 Vulkan 端口** PASS(无 JIT); 产品侧 `agent.host` publish **EXIT=0 / IL 警告 0 / 原生 14.5 MB**。
- **全量回归 1060/1060 绿**(1051 + 新增 9); 全解决方案 build **0 Error**; 本轮触及文件**新增 warning = 0**(`BgeCpuEmbedder.cs` 的 CA2014 经 `git show HEAD:` 比对确认为既有)。

**本轮最贵发现: 循环头不能带条件分支(规范合法 ≠ 驱动接受)**
- 首版内核把 `OpBranchConditional(cond, 循环体, merge)` 放在循环头 ⇒ `vkCreateComputePipelines: VK_ERROR_UNKNOWN`, 而自写结构校验器判**合法**。
- 一次性探针 `/tmp/r393probe` 最小变体二分(不入产品): 纯逐元素 ✅ / 函数局部变量 ✅ / `OpUDiv` ✅ / **循环头带条件分支 ❌(守卫有无、内存访问有无、分支极性三种改法都红)** / **glslang 形状(循环头只 `OpLoopMerge`+无条件跳转, 条件判定独立块) ✅** ⇒ 唯一变量是控制流形状。
- 修复采用 glslang 形状, 并**机检固化**: `MatMulBias_含唯一归约循环且循环头无条件分支` + 判别力负控 `MatMulBias_驱动约束检查器有判别力`(改回条件分支必须报 1 处违规)。

**内存观测(结论: 归因驱动, 不记为我方泄漏)**
- 原实现每次派发新建且从不销毁 6 类管线资源(真句柄泄漏) ⇒ 改造①按 (内核名,绑定数) 缓存; 改造②设备缓冲按 64 KiB 档位池化; 改造③命令缓冲常驻 + `ResetCommandPool`。
- 三次改造后 **RSS 斜率均不变**(≈76 KB/派发, 72/432/864 次派发实测), 而池读数证明我方有界: `pool{classes=5 slots=7 leases=3456 reuses=3449}`(**864 次派发只用 7 个设备缓冲, 复用率 99.8%**)。
- ⇒ 剩余增长落在 **lavapipe(软件 Vulkan ICD)内部**, 真 GPU 必须重测; **不记为我方泄漏, 也不声称已解决**(三次改造各有真实收益: 消除句柄泄漏 + 消除每派发 SPIR-V 重编译, 后者实测 `ms_per_embed` 693→558)。

**诚实边界**:
1. 本机唯一 Vulkan 设备是**软件实现**(llvmpipe) ⇒ 端口在本机比 CPU 慢(≈588–693 ms vs ≈249–259 ms/嵌入); **不提出性能承诺**, 真 GPU 复测判据/命令见报告 §6。
2. **产品侧未接线**: `agent.host` 进程内选 `vulkan` 需把 Vulkan 共享源接进产品并引入 Silk.NET, 会带入 6 条第三方 IL 警告 ⇒ **须用户决策**(本轮不擅自破坏既有边界)。
3. 循环控制流约束来自本机唯一驱动实现; 换驱动须复跑 `--selftest`。
4. 长文本(seq→510)只做了内核级数值对账(探针 `512×2048`), 未做端到端对账。
5. 踩坑: 给 `agent.host` 追加命令行 `-p:PublishAot=true` 会全局传播并命中 `netstandard2.1` 的 `agent.io` ⇒ `NETSDK1207`; 正确做法是只用 csproj 内置 `PublishAot`。

## R392 — 模块重命名 click-rover → agent.rover(目录/项目名/内部文件夹/命名空间全部小写, 类名不动)

**用户令 (逐字)**: "click-rover 更名为agent.rover 并且内部文件夹 类文件的命名空间 也需要小写 （类本身不用）"。

**因果链**: 模块名 `click-rover` 带连字符 ⇒ (a) 命名空间 root 只能写 `clickrover`(与目录名不同形, 二者漂移), (b) 内部文件夹首字母大写(`Cli/Gguf/Gpu/Spirv/...`)与命名空间 `clickrover.cli` **大小写不一致**, 同一目录在路径与符号里两种写法 ⇒ 引用面靠人记忆同步, 一旦不同步就是"编译过得去、文档与路径对不上"的静默漂移。R392 把**目录名 = 项目名 = 程序集名 = 命名空间 root = 文件夹名** 收敛成**同一串小写标识** `agent.rover`, 使"名字只有一处真值"; 同时保留类名(在 `.sln`/文档/registry 中作为符号引用, 改名无收益却有回归风险)。

**交付(全部带真机/机检证据)**:
1. **重命名映射(34 文件 + 1 计划文档)**: `src/click-rover` → `src/agent.rover`; csproj `click-rover.csproj` → `agent.rover.csproj`; `AssemblyName`/`RootNamespace` = `agent.rover`; 内部文件夹 `Cli→cli` `Formal→formal` `Gguf→gguf` `Gpu→gpu` `Gpu/Spirv→gpu/spirv` `Infer→infer` `Quant→quant` `Runtime→runtime`; 命名空间 `clickrover.*` → `agent.rover.*`。全部走 `git mv` + 脚本化文本重写(**不留人手抄**)。
2. **消费侧引用面同步**: `src/agent/agent.csproj` 共享源 `../agent.rover/formal/*.cs` + `../agent.rover/gpu/spirv/*.cs`(Link 同步小写); `eval/dcr/harness/dcrval.csproj`; `SpvRegistryAuditTests`(机检路径 + 目录探测); `docs/verification-registry.json` 的 `evidence_path`(**机检校验路径存在性, 不更新即红**); `scripts/kpi_dcr.py` / `eval/dcr/*` / plans / reports。
3. **解决方案接入(补齐 `agent.rover` 长期缺口)**: `dotnet sln agent.sln add src/agent.rover/agent.rover.csproj` ⇒ 工程数 16→17, 全解决方案 build **0 Error**。
4. **契约标识同步**: 插件 id `clickrover.formal` → `agent.rover.formal`(消费侧与契约文本同源常量 `FormalPromptContract.PluginName`/`ClickRoverSegmentPlugin.PluginId`, 由机检保证一致)。
5. **残留检查 = 0**(除已发布 HTML 报告逐字未动, 保其 sha256)。

**真机基线(重命名后, 与重命名前逐项对照)**:
- 全量回归 **1051/1051 绿**(与 R391 基线**同数**, `/tmp/r392/full_test.log`, 31 s; 干净无并发)
- 解决方案 build **0 Error / 66 Warning**(66 = 既有 warning 存量, 非本轮新增)
- **数值不变**: tiny 前向 `topk{rank=1 id=46 logit=4.420093}` 与 R388b 记录值**逐位相同** ⇒ 重命名未触碰任何计算
- 内核 `check --selftest` **14/14**(tokens=0); 驻留 `residency --selftest`(真 7B Q4_K_M) **10/10**
- Vulkan 真机: `done{command=vulkan kernels=3 pass=3 fail=0 spirv_valid=3 neg=5/5}`; `meta` 正常
- **AOT 发布复验**(改 agent 链代码后可执行产物必重发布): R391 收尾与 R392 各跑一次 `dotnet publish src/agent.host -c Release -r linux-x64` ⇒ `EXIT=0`, **IL 警告 0**, 产出原生 `agenthost`(NativeAOT, 无 JIT)

**附带发现并修复: 仓库内两份 DCR eval 快照是 R387 旧物(重命名逼出的真 bug)**
- **触发**: 按"改名后必须用真产物复验数值不变"的纪律复跑装配层评测, 发现仓库内 `eval/dcr/assembly_out.jsonl` / `eval/dcr/kernel_out.jsonl` **不是 R388 权威快照**, 而是 **R387 时代旧物**(各含 32 条 `Unknown`) ⇒ 与 R387 记录的 **DCR 132/145 = 91.03% / 覆盖率 60.69%** 对应, 比 R388 修内核后的真实值低 **13 条**。
- **根因**: R388 的真装配复跑产物落在 `/tmp/r388/`, **仓库内那份从未同步** ⇒ 临时目录里的权威快照 ≠ 仓库里的权威快照(同类根因: R390 的"跑旧 DLL"假象)。
- **修复**: 由**仓库内产物**复跑并**直接覆盖仓库文件** —— 装配层 = **AOT 原生产物** `agenthost --formal-eval eval/dcr/dcr_cases.jsonl`; 内核层 = 重命名后 `agent.rover check <case>.assert --json` ×145; 随后 `scripts/kpi_dcr.py` 重生成 `eval/dcr/dcr_report.txt`。
- **零漂移证明(两条独立腿, 各 145/145、0 差异)**: 新装配快照 vs R388 真装配快照 `field_diffs=0`; 新内核快照 vs R388 内核快照 `field_diffs=0`(**含 `note` 与反例变量取值**) ⇒ 重命名未改任何判定; 顺带 `ms` 由 R388 的 ~32.7 ms/条降到 **~0.18 ms/条**(AOT 免 JIT, 旁证)。
- **刷新后权威结论**(R392 历史读数; **R397 起单一口径定稿**, 禁止再并列汇报): **DCR(弃权计合规) 145/145 = 100.00%** / **保守口径 101/145 = 69.66%**(= 可决断集上限) / 覆盖率 101/145 = 69.66%(Proceed 51 · Violation 50 · Abstained 19 · Malformed 25) / 六类一致率**全 100%** / **主动误判 0**; z3 独立审计重跑 `AUDIT_RESULT=SOUND`(**30/30 反例为真 · 33/33 Proved 确 unsat · 0 假**), 与题集自带 `expected_verdict` **145/145 一致**。
- **文档同步**: `eval/dcr/README.md` §4.1/§4.2、`docs/reports/r385/dcr-s3-s4-results.md`(§4 标为 R387 留痕 + 新增 §8)。
- **新纪律**: 凡涉及仓库内 eval 快照的轮次, **必须用仓库内相对路径复跑并覆盖仓库文件**, 禁止只在 `/tmp` 留证。

**诚实边界**:
- 类名按用户令**不动**(`ClickRoverSegmentPlugin` 等), 因此"符号层"仍含 `ClickRover` 词形 —— 这是用户明示的取舍, 非遗漏。
- 计时类微基准 `SessionPerformanceTests.GetRecentMessages_BeatsFullTableSort_AtScale` 在与 build **并发**时出现过一次假红(`new 191µs < old/3 109µs`, old 被并发拉快); **无并发单跑 4/4 绿、全量单跑 1051/1051 绿** ⇒ 判为 2 vCPU 争用下的噪声, 非重命名引入。
- 已发布 HTML 调研报告内 2 处 `click-rover` 字样**故意不改**(线上产物 hash 已交付, 改动即换版)。

---

## R391 — 形式化闭环挂上主链(计划节点级本地验证 + 静态前缀条件契约注入)

**用户令 (逐字)**: "继续下一轮, 并结合当前 agent 能力做一次能力精简归拢(不必要的能力与步骤可以合并降低复杂度) 并于形式化验证引擎高度规划最合理的 agent 执行链" + "新 agent 链的计划要达到外部最强工程化实现给出的决策合规率为 90.5% 的 ±5 个百分点左右" + "进行下一步直到目前所有计划的任务全部完成"。

**因果链**: R386–R390 把形式化内核/闸门/GPU/驻留都做成了**独立可证伪件**, 但 agent 侧只到"闸门能拦节点" —— 模型**不知道**要产出形式化符号(C8 缺), 也没有一个"节点自带断言 ⇒ 本地裁决"的执行路径(C7 缺)。两者缺一, 内核就永远只是旁挂的评测件, 进不了主链 ⇒ 本轮把两侧接起来, 并让**注入侧与消费侧共用同一套围栏语义**(单一事实源 `ClickProofFence`), 否则会出现"注入了却读不到"的静默断链。

**交付(全部带真机/机检证据)**:
1. **C8 · 静态前缀条件注入**: `FormalPromptContract.Build()`(契约段: clickproof 围栏语法 + `no_formal: <理由>` 逃生口 + 逐条禁令) +
   `SessionBaseline.Build(root, formalPluginPresent)` **双槽缓存**(槽0=不在场 ⇒ 与 R380 前缀**逐字一致**, 零 token 负担; 槽1=在场 ⇒ 追加契约段)。
   **为什么必须双槽**: 单槽缓存会把两种前缀串味(先到的赢) ⇒ 前缀随调用顺序漂移 = 可复现性与缓存命中率**一起崩**。
   真机(生产组合根): 前缀 2800→3391 字符(+591, 估算 +358 token, 常量进静态前缀后每轮命中), 不在场前缀不含 clickproof。
2. **C7 · 计划节点级本地验证**: 节点正文自带机器可读断言 ⇒ `PlanRoutePolicy` 判 `Local` + `formal.verify` 执行器(`CarriesFormalClaim` ⇒ `ClickProofFence.ExtractTrimmed` 命中);
   执行器四态不可混算 —— `Proved`⇒放行 / `Refuted`⇒阻断且反例回注 / `Vacuous`⇒拒绝 / `Unknown`⇒**Failed 且 disposition=Abstained**(诚实弃权: 不计违规, 一样不放行);
   缺失(`NoFormal`)⇒放行且**绝不为此追问 LLM**(`RequiresLlmRetry` 恒 false)。
   真机(容器内**无任何 LLM 提供方**): `C_route location=Local exec=formal.verify`; n1 Proved⇒Completed, n2 Refuted⇒Failed, **total_llm_tokens=0** ⇒ 若误判远程必然硬失败。
3. **消费侧恒等透传铁律**: `ClickRoverSegmentPlugin` 处理含围栏段时返回内容与入参**逐字相等**(真机 `B_segment_identity=True`), 裁决只落账不改正文 ——
   段插件在回复链上, 改写正文会同时破坏缓存命中率与可复现性。
4. **同源封死静默断链**: 围栏标识与插件 Id 由注入/消费两侧**共用常量**, 机检 `Contract_Ids_Match_Consumer_Side` 钉死; 路由谓词亦与提取器同源(机检 + 负控: ```python 围栏/散文不得判本地)。
5. **一次真红并修**: 全量跑出 1 例红灯 `Unknown_Abstains_And_Still_Does_Not_Pass` —— 根因是执行器自造了第二套 Fall 文案, 与闸门不同源;
   改 `PlanNodeFormalGate.BlockMessage(d)` 后转绿。**该断言确实绑定了组件真实行为**(只查枚举名/恒真判定的空心断言不会红)。

**基线**: 三新套件 **26/26 绿**(契约 7 / 插件 8 / 执行器 11, 逐套件计数与 `--list-tests` 相符); **全量回归 1051/1051 绿**(上一基线 1025 ⇒ 净增 26, log `/tmp/r391/full_test.log`); 真机探针 11 条判据全绿(`/tmp/r391probe`, 生产组合根 `AddAgentFramework()` 装配, 原始输出 `/tmp/r391/evidence.log`)。

**诚实边界**: ① 本轮**不宣称** DCR 达标 —— FAVA 的 DCR 公式/分母/弃权处置仍不可得(T1–T4 开放), 仍须双口径敏感性分析;
② `Unknown⇒节点 Failed` 是**执行策略**(未证明不放行), 与 DCR 台账"Unknown 计合规(弃权)"是两个层级的口径, 不可混算;
③ 上游围栏回退(执行器支持)与路由判据(只看本节点正文)**不同宽** —— 已把"断言必须落在验证节点正文"写进 C8 契约第 5 条, 但**模型是否照做尚未在带 LLM 的真机会话里验证**;
④ token 增量为估算口径(中文 ~1 token/字), 非分词器实测。

---

## R386/R387 — 形式化闸门接线(调度器唯一前门) + 断言契约层 + 等待墙钟锚点 + DCR 评测入口

**用户令 (逐字)**: "进行下一步直到目前所有计划的任务全部完成"。

**交付(全部带真机/机检证据)**:
1. **M1 删空抽象层**: `ICapabilityPlugin`/`CapabilityPluginRegistry` = 零实现零注册(仅定义+一个 `FakePlugin` 测试) ⇒ 删两文件;
   **反证**: 删除后全量构建 0 错、全量测试绿 ⇒ 确认无消费方。M2 能力来源唯一: 保留 `CapabilityScanner` + `PanelData.CapabilityEntry`(全仓唯一定义)。
2. **断言契约层** `FormalAssertionContract`: 缺省(未声明)⇒`NoFormal` **放行且绝不为此追问 LLM**; 显式 `no_formal: <理由>` ⇒ 放行;
   `no_formal` 与 premise/goal 并存(自相矛盾)/残缺(缺 premise 或 goal)⇒`Malformed` 阻断。21 例单测含负向控制。
3. **节点级形式化闸门 — 第一次插错位置, 被真跑机检抓出**: 初版插在 `PlanRunner.RunNodeAsync`(产品路径的私有方法) ⇒
   端到端接线测试显示"被反驳契约的节点**执行体仍被调用**"(`order=["a"]`) ⇒ 说明该点**不是唯一前门**。
   迁到**调度器唯一前门** `TaskPlanExecutor.RunNodeCoreAsync`(任何被注入的 nodeRunner 都绕不过)后: 被反驳/片段外节点**零调用**且终态 `Failed`。
   **这就是"接线测试必须驱动真实调度器"的实证价值** —— 单测全绿但闸门在真链路上不生效, 只有端到端断言能暴露。
4. **内核语义修正(契约与实现不一致)**: 文档契约写"片段外一律 `Unknown`", 实测非线性前提(`x * x == 4`)被判 `Malformed` ⇒
   会把**正确弃权误记成畸形**, 直接扭曲 DCR 口径。修 `FormalKernel.FromParseFailure`: 片段外⇒`Unknown`(附 `fragment_limit:` 理由码), 真语法错仍 `Malformed`。
5. **`--formal-eval <cases.jsonl>`**(真实装配判定层入口, 零 LLM/零 daemon/零 shell): 8/8 冒烟覆盖 absent / declared / proved / refuted(附精确反例 `x=32818, y=-32808`) /
   vacuous / fragment(`Abstained`) / malformed / 自相矛盾; 每行 `would_call_llm=false`。**这是 DCR 可证伪测量的接口**。
6. **WaitUs 墙钟锚点**(R384 遗留⑤: 跨进程不可对账): `NodeWaitRecord` 增 `Started/EndedWallUtcMs` + `End()` **单一写点**(禁止两处各自取时钟) +
   3 条对账判据(`WallClockReconciled` / `WallClockOrdered`) + 负向控制(人为倒流必须判否)。时长唯一事实源仍是进程内单调时钟。
7. **R384 遗留④复核结论**: "答复落点与主链 `AnswerSink` 不一致" —— **`AnswerSink` 全仓 0 命中, 前提失效**; 真实落点是 `PlanResumeService.ApplyReply`(:206, 槽位名+范围校验, 不满足即拒绝)。
8. **登记**: `docs/verification-registry.json` 增 3 行(`formal.contract` L2 / `formal.node-gate` **L4** / `plan.wait.wallclock` L2), 机检 `VerificationFormTests` 6/6。

**基线**: 全量 **1019/1019 绿**; 闸门+接线 28/28; 契约 21/21; 墙钟+等待 35/35; 机检 6/6。

**诚实边界**: FAVA 原文正文(arXiv HTML/PDF/ar5iv/alphaXiv)本次均只取到摘要与引言 ⇒ **DCR 公式 / 分母 / 弃权处置 / aggregate 合并方式(T1–T4)仍未知**;
故 DCR 报告必须给**双口径敏感性分析**(弃权计合规 / 不计合规), 不得只报一个数。

---

## R380 — 缓存命中率口径修订(首要KPI) + 越线必查闸门 + 会话稳定基线 + 视觉能力目录纠偏

**用户 OOB (逐字)**: "将缓存命中率计算只计算需要命中的部分，当前轮新增不计入，因为肯定不触发缓存，并且记录到KPI首要任务内，一旦越过红线必然检查问题为什么发生并修复" / "将之前的红线提高为95%"

**口径修订**: 有效命中率 = `hit / min(本轮 prompt, 上一轮同会话 prompt)`
—— 旧口径 `hit/(hit+miss)` 把"本轮新增"(必然不命中)算进分母, 会把**已到结构极限**的轮次误读成灾难性失败
(真机 mt_fix4 轮2: 旧口径 66.08% vs 新口径 91.34%; 而该前缀的理论上限恰为 91.34%)。

**算术判决 (真机两样本一致)**: 命中 = `(floor(前缀/64) − 1) × 64` ⇒ 上限 ≈ `(n−1)/n` (n = 前缀 64-token 单元数)
⇒ 95% 需前缀 ≥2496 token (n≥39)、98% 需 ≥6336。**这是"红线提高必然要求前缀加厚"的定量依据** —— 结构修复到极限也只是把命中吃满上限。
实测校验: 前缀 981 → 上限 896 (观测 896)；前缀 2001 → 1920 (观测 1920)；前缀 2428 → 2304 (观测 2304)。

**修复**:
1. `PromptCacheKpi`: 口径 + `HitCeiling` + `PrefixTokensNeededFor`；**修未上报冒充 0 命中的真 bug**(机检抓到)。
2. `PromptCacheRedline`: 阈值 90%→**95%**；`Violated` + `Diagnose` (按四类破坏点给出可执行清单 + 算术判决)；router 越线即 `LogWarning` + `cache_redline_violation` 打点。
3. `SessionBaseline` (~3k 字符): 会话首轮焊进前缀 (纪律/命令/工作区快照/能力/模块地图/失败模式) —— 红线 95% 的算术必需项（**R394 已提高为 97%，本句为当时阈值**）, 之后每轮命中该段, 增量成本≈0。
4. `ModelQueueRouter` 逐轮归属打点 `cacheable_tokens`/`effective_hit_rate`；`scripts/kpi_cache_hit.py` 重写为首要 KPI (按轮次/会话聚合 + 红线判定 + 越线清单 + 退出码 -1 可做门禁)。
5. **模型目录纠偏 (真机实测推翻配置)**: `deepseek-flash` 原记 `image_input: false`, 实测其 API **支持图像输入** (读出测试图的"红色/SCORE 7/GAME OVER") → 改为 `true` (截图检验通路)。

**验收**: 机检 9/9 (PromptCacheRedlineTests: 口径/未上报/红线/上限公式/带内全扫/负向控制/真机回归)；真机 3 轮 (mt_fix5/6/7) 待汇总; 全量测试待跑。

**诚实边界**: 95% 在**短会话第 2 轮**仍可能因单元边界对齐而摇摆 (实测 95.95% / 94.90%) —— 加厚前缀后进入 ≥96% 区间; 与提供方实现相关的精确损耗模型仍需更多样本标定。

## R379 多轮会话缓存命中率根因修复 — 追加式前缀 + 增量最小化 (868/868)

**用户口令 (逐字)**: ①"关于目前命中率非常低的问题出现在哪里？一般不是90%多命中么？" ②"上下文 2000 token 预算 再自检的时候改成1M" ③OOB 红线: **多轮会话第 2 轮起命中率 ≥90%, 目标 98~99%**。

**根因 (请求体 dump + 最长公共前缀, 决定性实测; 官方规则: 缓存单元 64 token, 必须自 token 0 起完整匹配)**:

| # | 破坏点 | 位置 | 实测后果 |
|---|---|---|---|
| ① | `messages[0]` 逐轮改写 (forecastHeader 入 system + **意图漂移** search→general) | `IndustrialAgentV2.cs:1040-1049` / `:1035` | 第 2 轮 system 440→448 字符 → 公共前缀仅 **1.4%**, 自字节 93 断裂 |
| ② | 历史**滚动摘要重写** + `Take(10)` + **2000 token 预算砍头** | `IPromptBuilder.cs:197-215` | 第 3 轮命中率 **0.00%** (答案被压成 79 字符) |
| ③ | 回注块在 `SentContent` 快照**之后**追加 | `IndustrialAgentV2.cs:1232` | 发送字节 ≠ 回放字节 (实测差 72 字符) → 前缀中部断 |
| ④ | 每轮增量 ~850 token 而会话前缀仅 ~970 token | 装配点 | 命中率**算术天花板 ~53%** |

**修复 (追加式前缀 + 增量最小化)**:
1. **追加式回放**: 历史不重写/不砍头, `maxHistoryTokens` 2000 → **1,000,000** (用户令); 每轮重建的上下文块移到历史**之后**; `forecastHeader` 移出 `messages[0]`;
2. **`messages[0]` 会话内冻结** (`FrozenSystemPromptTable`): 意图漂移不再改写 system, 改为尾部一行短提示 `[本轮意图] general (会话人格保持不变)`;
3. **回注回写 `SentContent`**: 发送字节 = 回放字节 (单一事实源);
4. **增量最小化** (`SessionInjectionPlanner`): 会话静态块 (画像/偏好/工作区) 首轮焊进前缀、之后不再重复; 动态块**跨轮字节 + 近重复 (trigram Jaccard ≥0.75) 去重**; 用户本轮原始问题永不参与去重 (安全边界);
5. **KPI 逐轮归属**: `Prompt.SessionId`/`TurnIndex` → `llm_call` 打点 `agent_session`/`turn`; `scripts/kpi_cache_hit.py` 增按轮次/会话聚合 + **红线判定** (多轮第 2 轮起 ≥90%)。

**机检 (9/9, 含负向控制)**: `MultiTurnCachePrefixTests` 4 (逐字节追加式前缀 / 红线占比 / 负向控制: 变量放 system 必须破前缀 / 1M 预算不丢消息) + `SessionInjectionPlannerTests` 5 (静态块识别 / 跨轮去重 / **红线: 增量占比 ≤10%** / 标题行恒保留 / 近重复抑制)。

**真机 4 次复测 (单会话 3 轮, 每轮请求体落盘)**:

| 口径 | 轮 1 | 轮 2 | 轮 3 |
|---|---|---|---|
| R379 基线 (修前) | 30.26% | **62.28%** | **0.00 / 13.66 / 11.82%** |
| R379 修后 (mt_fix4) | 13.05% | **66.08%** | **72.44%** |

- 结构指标: `messages[0]` 会话内恒定 **1149 字符** (修前 440→448); 轮2→轮1 公共前缀 **99.4%**, 轮3→轮2 **99.6%** (逐字节追加); 每轮调用数 1 (修前第 3 轮 3 次调用), 前缀不砍消息。
- 增量构成 (轮 2, 526 字符): 问题 13 + 意图提示 26 + 下轮预估 32 + SessionMemory 84+24 + **Memory(RAG) 261** + 回注 12 + 联想 27+29。

**诚实边界 (未达红线)**:
- 轮 2/3 = 66.08% / 72.44%, **红线 90% 未达**。算术: 命中率 ≈ 已发前缀 token / 本轮总 token; 要 ≥90% 则**每轮增量 ≤ 前缀/9**。现前缀 981 token, 增量 ~375 token (RAG 140 + 记忆 60 + 联想 30 + 估/意图 30 + 回答 90 + 问题 7) → 上限 ~72%。
- 每轮"必须发"的只有回答 (~90) 与问题 (~7); 其余全是逐轮注入 → **要么停止逐轮注入新召回 (追问轮), 要么把会话稳定前缀做厚到 ~3000 token**, 二者皆是产品策略选择 (质量 vs 缓存 KPI), 待用户裁定 (本轮已把可无损失拿到的部分全部拿到: 静态块提升 + 近重复抑制)。

## R377 DS prompt 缓存命中率纳入优化 KPI（用户钦定）— 解析 + 三处打点 + 离线聚合 (859/859)

**状态**: 已实施并验证（L2 机检 12/12 + L3 真机样本 + L4 负向控制；AOT 参考 13,959,760 B / 0 IL，按 R7 不登记）

- **口径（用户 2026-09-13 钦定）**: 模型返回的 `usage.prompt_cache_hit_tokens` / `usage.prompt_cache_miss_tokens`
  → **命中率 = hit / (hit + miss)**，作为 **K2（token 使用量）成本侧子指标 K2b** 纳入优化 KPI。
- **实现链路**: `OpenAIChatUsage`(+2 可空字段) → `QueueResponse` / `LLMResponse`(+2 字段) → `ModelQueueAdapter` 透传；
  新增 `PromptCacheKpi`（4 位小数 + 未上报哨兵 `-1`）；**三处** data-carrying `llm_call` 打点（主路径 / 重试 / 兜底）都铺
  `cache_hit_tokens` / `cache_miss_tokens` / `cache_hit_rate`；离线聚合 **`scripts/kpi_cache_hit.py`**（按模型分组 + 未上报计数 + JSON 落 `eval/results/`）。
- **铁律（诚实边界形式化）**: **未上报 ≠ 0 命中** —— provider 未给字段时记 `-1` 且**不并入比率**；分母为 0 同样记 `-1`。
  真机实证该区分有效: 全量遥测 45 次调用中 **41 次未上报（历史无此字段）+ 4 次上报**，脚本如实分列，**不把 41 次读成 0%**。
- **真机样本（同题贪吃蛇连跑 2 次；`/tmp/gameprobe/run_r377.sh`）**:

  | 跑次 | 调用 | tokens | hit | miss | 命中率 | 产物 | D3 修复回流 |
  |---|---|---|---|---|---|---|---|
  | RUN1 | 2 | 37,226 | 1,280 | 4,114 | 23.73% | 2（首投 exit=1 → 修复 exit=0） | 触发 1 次 |
  | RUN2 | 2 | 39,955 | 2,048 | 3,496 | **36.94%** | 2（首投 FAIL 14/16 → 修复 ok 16/16） | 触发 1 次 |
  | 合计 | 4 | — | 3,328 | 7,610 | **30.43%** | — | 2/2 成功 |

  **独立复核**（自己跑闸门，不信遥测自报）: RUN1 `py_8606386f --selftest` → `exit=0 · ALL PASS (16/16)`；RUN2 `py_a7fa39a7` → `exit=0 · ok (16/16)` ✓。
  第二次命中率更高（23.73% → 36.94%）= 同一前缀被复用，KPI 方向符合预期。
- **机检**: `PromptCacheKpiTests` 12/12（DTO 解析 / 未上报为 null / 命中率边界含真·0 命中 / 三元组固定 / **按打点块配对**的接线扫描）。
- **负向控制 3 组**: ① 命中率分母 +1 → **4 红**；② `HitTokens(hit) => hit ?? 0`（未上报冒充 0）→ **1 红**；③ 删一处打点铺设 → **1 红**。
  **首跑变异③ 曾 0 红** —— 我的扫描断言当时只数「助手出现次数」（空心判定）→ 改为**按打点块配对**（每块必须真含 `cacheKv[0], cacheKv[1], cacheKv[2]);`）后抓到。
- **诚实边界**: ① 命中率为 2 跑样本（同题），非稳态生产分布；② 本轮样本 tokens（37.2k / 40.0k）高于 R376 的 19.2k，
  原因是**两次首投产物自测均失败 → D3 修复回流各多 1 次调用**（机制正常工作，成本如实登记，不做"优化了"表述）；
  ③ 首跑全量 857/859（2 红未留名）→ 随后连续两跑 **859/859**，判负载偶发（同 R374/R375 类）；**下轮候选**: socket 测试族串行化以消抖。

**基线**: 全量 **859/859**（R376: 847/847）；命中率 KPI 首发样本 30.43%（4 次调用）。

---

## R376 exp2 P2 达成 — 真机同连接 menu 闭环 + 两处断链修复 (⑪ 握手残包 / ⑫ 回程饿死) (847/847)

**状态**: 已实施并验证（L2 机检 + L3 真机闭环 + L4 负向控制；AOT 按规范 R7 本轮不登记）

- **靶点**: R375 遗留的 P2「真机 `chat.send` 收不到结构化 ask 事件」。
- **根因（遥测实证，非推测）**: R375 同题遥测 `evidence_gate{subtasks:1,suspects:0,to_ask:0,confidences:"1"}` —— 清晰题置信度 1.0 ≥ 0.60 阈值，**证据门根本没触发**（不是通道坏）。
  触发配方由代码给出（`IntentDecomposer` 启发式，0 token）: 指代不明 −0.25 + 通用意图弱信号 −0.20 → **0.55 < 0.60**。
- **真机闭环（P2 达成）**: 新探针 `/tmp/fp376/probe2.py`（AOT 二进制 + 真 TCP + 真 token）连跑 3 次全部走通:
  `ask 事件`（`ask-*`，`timeout_s=300`，`questions[1]`）→ **同一连接** `ask.reply` → `resp{outcome:answered}` → `ask_closed{answered}` → **续跑返回真实正文**。
  遥测: `evidence_gate{subtasks:1,suspects:1,to_ask:1,confidences:"0.55"}` + `loop_turn{total_ms:4054,success:true,reply_chars:119,asked:true}` → `gate_to_ask=True`（R375 为 False）。
- **顺带修两处真缺陷（真机暴露，均带负向控制）**:
  - **⑪ 帧边界 / 握手残包**: `FrontendApiServer.TryAuthHandshakeAsync` 单次整块读取后**丢弃换行之后的字节** → 客户端把 auth 与首个请求合并发送时首请求静默消失（R375 探针靠 `sleep 0.8` 绕行）。
    修复: 握手返回残包 `Tail`，请求循环**预置缓冲并先排空**，不丢字节。
  - **⑫ 同通道回程饿死（更严重）**: 读循环 `await` 请求执行 → 请求处理内部触发 ask 并等答复，而答复在**同一条连接**上永不被读 → 双向死锁至 300s 超时。
    **单测全绿的原因** = 触发源被**带外构造**（直接调 `RequestCredentialsAsync`），读循环空闲 → test-blind-spot。
    修复: 读循环只做**解析 + 并发派发**（`Dispatch`: 在途上限 8、异常必观测、发送面共用连接锁保证行不交错），断开前给在途请求 2s 有界收尾。
- **契约澄清（已入 registry）**: ① 并发派发下响应**按 `req_id` 关联**，不保证到达顺序；② 同通道上**事件与响应相对顺序不保证**（测试断言改为顺序无关且暂存不丢）。
- **机检**: 新增 `FrontendHandshakeTests`(4) + `FrontendAskSameConnTests`(2)；过滤族 **23/23**；全量 **847/847**（R375: 841/841）。
  **负向控制 2 组**: 丢弃握手残包 → **2 红**（两种变异各 2 红）；读循环改回等待长任务 → **2 红**（均已还原，字节一致）。
- **能力探针（R376 回归样本，同题贪吃蛇，CLI 主链）**: 1 次调用 / 76.7s / **19,191 tokens** / 产物 14,368 B `origin=fenced` / `script_run exit=0`；
  **独立复核** `python3 -I <产物> --selftest` → **exit=0 · PASS (34/34 项)**（不信任遥测自报）。
- **通用教训沉淀**: `skills/delivery-selfcheck/SKILL.md` → v1.1.0 新增「步骤 6 · 通道核查」（帧边界 + 回程饿死 + 有界并发 + 顺序无关）；
  「正文核心零语言特性」机检 **19/19** 通过（含负向控制：注入语言 token 必红）。
- **诚实边界**: ① 真机样本 n=3（同题三次均闭环）；② tokens 19,191 vs R375 17,188（**+11.7%**，产物自测项 34 vs 13，单样本、模型侧生成差异，非机制开销）；
  ③ 在途请求**不随客户端断连取消**（2s 收尾后放弃，与修复前同语义，登记为已知边界）；④ exp2 §8 Q1–Q4 仍**待用户裁决**（本轮沿用 R375 推荐口径）。

**基线**: 全量 **847/847**；AOT 参考 13,959,712 B / 0 IL 警告（按 R7 仅作参考，不登记）；提交见本轮 commit。

---

## R375 exp2 P0 前端 menu 问询通路实装 — 信封 + 事件推送 + ask.reply/ask.cancel + 选项贯通 (841/841)

**状态**: 已实施（L2 机检 + L3 真机接线证明；生产侧命中率 0/1 如实登记；AOT 按规范 R7 本轮不登记）

- **缺口（exp2 P0 三处）**: ① `FrontendPromptService` 的 `emitEvent` **无提供者** → 前端模式下问询事件直接消失（A 栈 `Options` 有字段、零消费方）；
  ② 事件**不成信封**（裸 `{ev:"ask",...}`，与契约 `{v,type,event,payload}` 不一致）；③ 选项/数据类型**只拼进 Display 文本**，前端无法渲染菜单。
- **实装**:
  - **契约面**: 新增 `src/agent.frontendapi/AskEnvelope.cs` — 手写 `Utf8JsonWriter`（零反射/AOT）产出 `{"v":1,"type":"event","event":"ask","payload":{ask_id,service,purpose,timeout_s,group_size,questions[]}}`，单题含 `data_type/multi_select/default_value/options[{value,label,recommended}]`；另有 `ask_closed{reason: answered|timeout|cancelled|superseded}` 与 `TryParseReply`（空 id / 非对象 / 非 JSON → 显式拒）。
  - **通道面**: 新增 `FrontendEventHub.cs`（进程内唯一出站口）+ `FrontendApiServer.EmitEventAsync`（已鉴权在线连接广播）+ **单连接发送锁**（事件与响应不再可能交织成半行）；`FrontendApiChatRouter` 新增 `ask.reply` / `ask.cancel` 路由；`FrontendPromptService` 支持超时 / 取消 / 被取代 / 幂等（`already_answered`）。
  - **模型面**: `CredentialItem` += `DataType/Choices/MultiSelect/DefaultValue`（+ `CredentialChoice`）；`ClarificationBatch` 结构化下发选项（不再只拼文本），回答仍走原 `PromptDataValidator` 选项校验 → 菜单选择是**真闭环**而非显示优化。
  - **主机接线**: `Program.cs` 在 `--frontend-api` 模式下**覆盖** DI 的 Console 实现（DI 单服务解析取最后注册者）→ `IndustrialAgentV2` 经 DI 拿到前端问询实现；服务器上电前挂接出站面。
- **机检**: 新增 `AskEnvelopeTests` **8/8** + `FrontendAskFlowTests` **6/6**（真 TCP + 真信封：事件抵达含 options / 回复后调用方拿到答案 / 未知 id 不误投 / 取消返回 null / 超时 1s / 幂等 already_answered）；原 `FrontendApiTests` 4/4 不回归。
- **负向控制（真红实测）**: ① 回退裸 `{ev:"ask"}` → 5 红；② `BuildQuestions` 丢 options → 1 红；③ `Complete` 去掉 ask_id 校验 → 1 红（防误投）。
- **真机（L3/L4，`/tmp/fp375/probe.py`）**:
  - **P1 确定性（真 `agenthost` 二进制 + 真 TCP + 真 auth token）**: `meta.ping ok` / 伪造 `ask.reply`、`ask.cancel` → `payload.outcome=unknown_ask`（**未接线时会是 `channel_unavailable`** → 据此证明真机 DI 已换实现且通道已挂接）/ 空 envelope → `error.code=bad_payload` / `state.snapshot ok`。
  - **P2 真实 `chat.send`（deepseek-flash，1 次）**: **ask 事件 = 0/1** → 模型走**散文澄清**（reply 前缀 `[隔离任务]`），未触发结构化问询。生产者存在（`IndustrialAgentV2.cs:1878` EvidenceGate 裁定；`NodeExecutionResult.cs:332` node.Clarifications）但本次判据未命中 → **只登记「机制已通」，不登记「管线会问询」**。
- **真机顺带发现（⑪类新断链）**: 前端**握手整块消费首帧** → 与 auth 同一 TCP 段到达的首个请求被静默吞掉（探针首跑无响应、客户端表现为挂起；加 0.8s 间隔即通）→ 下轮候选修复（残包交还主循环）。
- **能力探针回归样本（同题贪吃蛇，`/tmp/gameprobe/run_r375.sh`）**: 真机 **1 次调用 / 82s / 17,188 tokens**（prompt 2,359 + completion 14,829；`first_budget=32768` 生效、`truncated=false`、`empty_reply=false`、`content_len=16092`）/ 产物 `py_936eb4414f523505.py` **16,842 B** `origin=fenced` `compile_valid=true` `exit=0`；**独立复核**（不信任遥测自报：`python3 -I <产物> --selftest`）**exit=0 · 13/13 用例通过 · PASS** → R375 改动（仅前端模式路径）**未回归 CLI 主链**；同题 tokens: R373 基线 18,029 → **17,188（−4.7%）**。
- **基线**: 单元测试 **841/841**（R374: 827 + 信封 8 + 真 socket 6）；AOT 见下方参考证据（按 R7 非发布 tag 不登记）。

## R374 运行结果回流闭环 D3(自我迭代) — 失败输出回流 + 有界修复 + 复检 (827/827, AOT 0 IL 警, 13,842,384 B)

- **断链 D3(运行结果回流)**: 产物校验失败时, 运行输出(stdout/stderr/未通过用例)在插件内部被丢弃 — 台账/遥测只留一个 exit 码
  → 失败信息**从未回到模型上下文**, 「自测失败」与「任务结束」没有区别, agent 无法自我迭代。
- **数据面**: `ArtifactCheck`(失败类别/退出码/输出尾部/自测入口判据) 经 `IArtifactCheckSource` 上抛,
  路由器 `DrainArtifactChecks()` 聚合(含通过项 — 复检需要「通过」证据); 产物报告新增 `OutputExcerpt`(失败输出不再丢)。
- **闭环面**: `ArtifactRepairLoop`(主链交付段后接线) — 校验失败 → 失败输出 + 失败脚本 + **闸门契约** 回灌模型
  (`Intent=code_generation`, 复用 R373 首轮预算) → 修复轮产物重新过闸 → **复检铁律: 必须出现「新路径且通过」的产物**
  (同路径 = 内容未变 = 没修好)。有界 1 轮; 闸门 `AGENTFRAMEWORK_ARTIFACT_REPAIR`(默认开)。
- **机检**: `ArtifactRepairTests` **10/10**(含闸门契约/未通过用例摘要/最小改动约束的可见性断言; 摘要只摘原文行且上限 12);
  负向控制双向实证: ① `IsRepairable` 置 false → **4 红**; ② 复检放宽为「任意通过产物」 → 非确定性用例 **1 红**。
- **真机 A/B(同题 3 连跑, 同一二进制, 仅环境变量开合)**:

  | 臂 | 每题调用 | tokens 合计 | 最终交付有效 | 触发回流 | 修复成功 |
  |---|---|---|---|---|---|
  | A 回流关 | 1/1/1 | 50,885 | 2/3 | 0 | — |
  | B 回流开(旧提示词) | 2/2/1 | 88,435 | 2/3 | 2/3 | 1/2 |
  | D 回流开(新提示词) | 2/1/1 | 77,270 | **3/3** | 1/3 | **1/1** |

  铁证: D RUN1 `artifact_feedback{fixed:true, error_kind:run, ms:70465, tokens:23306, detail:复检通过 py_659e45659066faf1.py}`,
  且制品链 `py_b6ce831c168371b0 (run_exit=1) → py_659e45659066faf1 (run_exit=0)` 全在遥测里可核。
- **提示词改进(真机驱动, R374b)**: 修复轮必须写明**闸门契约**(`python3 -I <文件> [--selftest]`、无 stdin/TTY、要求退出码 0)
  + **未通过用例原文摘要** + **最小改动/不得回退** — 与 R371 D4 同类教训(组件入口约定不写进上游纪律 → 无从满足)。
- **诚实边界**: ① n=3/臂, 跨臂「最终有效 2/3 vs 3/3」是抽样, **不能当统计结论** — 可断言的是**机制**(触发/回流/复检/归因)
  与**失败才付费**(首投成功路径 1 调用 ~15.6-16.7k tokens, 与 A 臂同量级); ② 失败路径成本 +1 调用 +23.3k tokens +70s;
  ③ A 臂「交付了自测失败的产物」用户无感知(只在遥测), D 臂同类失败至少被如实标记(可观测性提升, 不等于修好了);
  ④ 修复成功率仍受模型能力限制(旧提示词样本 1/2)。
- **环境卫生教训(本轮实证)**: 探针脚本曾把 `AGENTFRAMEWORK_PY_RUN=1` **全局 export** 进 `dotnet test` 进程 →
  env 敏感用例(`PythonRunVerifierTests.闸门取值_只认显式开`)必红。已改为只对真机执行段注入; `env -u` 复跑 **827/827**。

## R373 首轮预算策略(接线缺口修复) + 经验沉淀为思考逻辑 skill (817/817, AOT 0 IL 警, 13,817,472 B)
- **断链 D8(接线缺口)**: 路由器的首轮预算策略实现正确、12/12 单测全绿, 但**调用方把任务分类硬编码成 "general"** → 策略永不触发(死代码)。
  修复 = `Prompt.Intent` 从真实上下文透传(意图识别 → 适配器 → 路由器) + **接线级测试**(经真实适配器驱动) + RED 控制。
- **真机 A/B(同题 3 连跑)**: 每题调用 **2→1** · 恢复触发 **3/3 轮→0** · tokens/题 **−32%**(18029→12289) · 墙钟 136s→64s · 有效产物 **1/3→3/3**;
  遥测归因 `first_budget=32768 / intent=code_generation`。**根因假说成立**: 推理与正文共享输出预算(修复后单轮 `reasoning_len=56033` 仍不截断)。
- **经验落库形态(R373 用户钦定)**: 可复用经验沉淀为**思考逻辑 skill**(`skills/delivery-selfcheck/SKILL.md`: 判据先行→完整性→预算→接线→归因),
  **核心判据零语言特性**(机检 + 负向控制); 真机 `skill_match top1` 命中(此前同一题错配 image-gen)。
- **新缺陷 D9-a(真机当场暴露并修复)**: 初版 `type: normative` → `skill_trigger=force` 把技能正文当答复直出(无 LLM 调用/任务被劫持);
  改 `knowledge_hint` 后命中仅注入知识, 回复仍走主链 → 产物 19172B 有效。机检已锁死形态。

## R371 能力差异探针(py 游戏) → 七处断链修复 + 无围栏代码入链(含归因) + 教训表/运行级验证收口 (802/802, AOT 0 IL 警)

- **用户指令 (逐字, 三条)**:
  1. "请将bge设置为静默后台长期任务，只用汇报给我之前的5个需求和 【通过查看自己的上下文来对比当前项目agent能力（通过py开发一个游戏）差异】 这项任务，你可以先内置py插件"
  2. "真跑 agent 产出的 artifact 自测 时记得将可复用的模块做成skill放在skills内，并且可以允许对已有skill进行优化、删除、更名等操作（注意所有代码类型的必须为通用形式），一切以KPI（tokens\用户回答频率不能高\回复质量，同一个问题优化前后需要多少tokens和多少轮）和通过上下文自检为要目的"
- **探针方法**: 同一提示词（Python 贪吃蛇 + `--selftest` 无头自测）→ ① 宿主侧一条链做完（**PASS**）；② 项目 agent 用 **AOT 真产物**跑 → 逐环节对比。
- **五处断链点（全部真机实证 + 修复 + 机检）**:
  1. **D1 空正文被判成功**（最严重）：`llm_call completion=8192(=上限)/content_len=0/reasoning_len=22633` 且 `loop_turn reply_chars=0 success=true`
     → 推理模型吃满输出预算，框架只对 HTTP 异常重试、**从不检查正文是否为空**。修 `ModelQueueRouter`：检测 → 升级预算(8192→32768)+抑制推理提示重试一次 → 仍空则**可见降级 + Success=false**；遥测不再无条件 `success=true`。
     **修复后真机铁证**：`llm_call_recover: first_content_len=0 → retry_content_len=11345, recovered=true`（同一天同一提示词，缺陷真实复现并被自动救回）。机检 `EmptyContentRecoveryTests` 3/3。
  2. **D4 裸代码 → 机器链全程不触发**：回复 9232 字符完整实现、却**零 `script_artifact` 遥测**、`data/artifacts/` 无新文件。
     排查先自证伪（围栏正则被怀疑转义写坏 → 用独立 Python 复算 C# 字面量 → **正则正确**）；真因=**输出纪律从未要求代码围栏**，
     而插件只认 ```python → 契约不匹配；且第 7 条"500 字以内"与"交付完整单文件"直接冲突。修：输出纪律第 9 条（代码必须围栏 + 解除字数限制）。
     修复后：`script_artifact py_4ec069d5.py 12156B compile_valid=true`，**复跑其 `--selftest` → PASS (18/18)**。
  3. **D2 发布产物不自带 config**：AOT 产物在仓库外 cwd 运行 → `模型目录为空`。修 `agent.host.csproj` 让 publish 携带 `config/{base,modules,env}`
     （凭据只存环境变量名）；验证 `CONFIG_SHIPPED=/tmp/pub_aot_r374/config/base`。
  4. **D5 运行级验证选参 + 结论上屏**：交互式产物被无参运行必然卡到超时；CLI 只显示编译结论。修：产物含 `--selftest` 时自动带参（保守），
     CLI 追加 `· run exit=<code> (<ms>)`（未开启不显示，不假装验证过）。
  5. **D6 相对路径 → 运行级验证假阴性**：插件传相对路径而子进程 cwd 被切到脚本目录 → `python exit=2 (50ms)` 秒退，与"真跑 PASS 18/18"矛盾。
     修：`Path.GetFullPath(scriptPath)`；**RED→GREEN 负向控制**（撤销修复 → `Expected 0 / Actual 2`；恢复 → 12/12）。
     **v2（真机 RUN3 驱动, R372）**: v1 上线后 3 连跑命中 **2/3**, 未命中那次正文带**中文 docstring** → v1 的 35% 散文闸门把**字符串字面量内部**的行当散文而误拒。
     修: 三引号状态机(串内行记中性 + 强制 `code=false`); 新增 `ResponseSegment.Promoted` 归因 + `script_artifact.origin`(fenced / heuristic) → 产物**来路可归因**。
     机检 **9/9**(v2 新增 3 例: 文档健全实现必须提升 / 归因字段 / 截断半份仍可提升)。
  7. **D7 截断正文被判成功**(RUN3 真机铁证: `completion_tokens=8192(上限) content_len=1209 success=true`, 正文停在 `start_len: int =` **半行**) —— D1 的姊妹病(D1=空正文, D7=半正文):
     修: `LooksTruncated` **纯语法判据**(尾部为 `= ( [ { , : + - * /` 或反斜杠 / 引号或围栏未闭合; 全角句号结尾不误报) → **升预算 + 断点提示的有界续写一次** →
     `MergeContinuation` 去重重拼(重叠 >=6 字符且含非空白才算证据, 纯空白重叠不删以免吃掉缩进); 续写为空则保留原文并如实标记; 始终落 `llm_reply_truncated` / `llm_call_continue` 遥测。
     机检 `TruncatedReplyRecoveryTests` **15/15**(真 HTTP 假端点; 完整正文 1 次命中零额外成本 / 续写空不假装完整)。
  6. **D4-b 无围栏代码 → 产物链仍不触发**（D4 的**提示词级**修复不确定：3 次真机仅 1 次带围栏）：
     改在**分段器**里做保守启发式提升（**零额外 token / 零额外轮数**）：`ResponseSegmenter` 在无围栏时定位"整段代码" ——
     取**首个代码行**起、至**最后一个代码行 + 紧接其后的空行/注释**止；段内散文占比 > 35% 即放弃（**宁可漏提升，不可误判**：误判会把散文当代码落盘/编译 = 假证据）；
     命中后渲染层自动补围栏 → 用户看到的输出同时被**规范化**。
     机检 `UnfencedCodeDetectionTests` **6/6**（含无围栏文本经路由器 → **真 `py_compile`** 落盘；3 项负向控制：纯散文不误判 / <8 行不提升 / 已带围栏不重复）；
     **RED 控制**：关闭回退 → 3 个用例如期变红。
     **算法教训（语言无关）**：*启发式边界的终止条件必须锚定"最后一个确证项"；弱证据（空行/注释）只能附着于确证项，不得凭相邻性把无关内容并入* —— 首版把"尾部空行"当延长依据，导致其后散文被吞进代码段（机检当场抓到）。
- **L5 运行级验证 (t8–t12)** 收口：默认关、零 shell、超时杀树、输出上限排空、结构化结果、插件接线；族内 20/20（含 300k 排空 / 路径含空格引号 / 闸门关不执行 / 相对路径回归）。
- **exp5 教训表（role 模块）核心**：`LessonGeneralization`（通用化机检）/`LessonTable`（FNV-1a 指纹 + 去重归并 + 版本游标 + STJ 源生成 + 原子写）/`RoleLessons`（无 role 不落盘且显式回报）；11/11 机检（A8 负断言：`py_compile`/`C#`/`.cs` 一律拒收）。
- **exp8 立项**（用户本轮新钦定）：[已验证产物 → skill 蒸馏 + skill 生命周期 + KPI A/B](docs/plans/v0.22.0-exp8-artifact-to-skill-and-kpi-ab.md)（设计文档，含 tokens/轮数/asked 率/质量 对照口径与 A1–A6 机检草案）。
- **静默后台**：bge 闲时训练 cron 改为 `deliver=local`（只落盘不打扰）；探针全记录 `docs/plans/v0.22.0-r371-capability-probe-python-game.md`。
- **真机 A/B（R372, 3 连跑）**: 产物命中 **1/3 → 2/3 → 3/3**；**有效产物 2/3**（RUN2 截断致 `compile_valid=false`）。
  **归因反转（诚实点）**: 3/3 全为 `origin=fenced` → 本轮命中率提升来自模型给围栏（D4 提示词纪律），**非** D4-b 启发式；若无 `origin` 字段会把功劳误记给启发式。
  **D7 真机首触发**: `completion=8192 / content_len=7510 / truncated=true / reasoning_len=20159` → 续写 `before=2735→after=7510 / still_truncated=true / recovered=false`（未救回，如实入库）。
  **根因假说**（下轮验证）: 推理与正文**共享输出预算**（D1 空正文 `reasoning=22633/content=0` 与 D7 同源）→ 正解是首轮按任务给足预算，续写仅兜底（省 tokens/轮数）。
- **基线**: 单元测试 **817/817**（R372: 802 = 778 + D4-b 9 + D7 15; R373: +首轮预算 12 + 技能通用化 3）/ AOT linux-x64 **0 IL 警告**, `agenthost` **13,817,472 B**, 发布自包含（自带 config）。
- **诚实边界**: ① 探针只覆盖"生成代码"单场景，未覆盖多轮迭代式修复；② 运行级验证默认仍关（需 `AGENTFRAMEWORK_PY_RUN=1`）；
  ③ D3（运行结果回流给模型以自我迭代）**未做**，登记待办；④ exp8 仅设计未实现；
  ⑤ D7 续写的**真机复现**尚未取到（RUN3 那次截断发生在修复前）；`llm.truncated.continue` 的 L3 证据列为下轮必取项；⑥ 引擎侧无"按预算主动分段"策略，截断仍靠事后补救。

---

## R370 验证形式入规范 + 跨会话检索 + 运行级验证 + 教训表(role) + bge 召回实测反转 (772/772, AOT 0 IL 警)

- **用户指令 (逐字, 两条)**:
  1. "继续下轮，注意别忘验证形式，要加入规范内，【通过查看自己的上下文来对比当前项目agent能力差异】并修复完善"
  2. "收集未来可用于bge-small-zh-v1.5基座的数据，并加入闲时训练计划，本机若无任务再执行就自动执行数据收集，训练bge版本，统计KPI不断择优，请你以确定性的召回率为目标不断优化bge-small-zh-v1.5 并生成每个版本小报"
  3. (后续) "注意别忘验证形式…和 之前的5个开发计划的实施" + "你需要实测它们用于召回的能力后再最终确定用哪个嵌入模型"
- **L1 验证形式入规范 (用户长期焦点, 本轮交付)**: 新增 [docs/验证形式规范.md](docs/验证形式规范.md) (证据阶梯 L0 未验证 → L1 静态 → L2 单测/组件行为 → L3 真机运行 → L4 对抗负向控制; 六条规则: 无登记=未验证 / 静态最高只能报 L1 / L≥2 必须负向控制 / 证据必须落盘可复查 / 表述纪律 / 登记表机检) + [docs/verification-registry.json](docs/verification-registry.json) (机读登记表, 含 `covers[]` 覆盖插件实现) + `src/agent.tests/VerificationFormTests.cs` **6/6 通过** —— 含**自检负向控制**: 注入 5 类缺陷 (缺负向控制/静态冒充运行/证据路径不存在/插件漏登记/等级越级) 全部被抓出。已挂 README + 总纲 §0-0 第 9 条。
- **L2 自上下文能力差异 + 首批修复**: 新增 [docs/plans/v0.22.0-l2-capability-diff.md](docs/plans/v0.22.0-l2-capability-diff.md) (16 项逐条对位, 判定只用 `file:line` 实证; 缺口清单 G1–G9 入长期看板)。
  - **F1 跨会话检索** `src/agent/session/SessionHistorySearch.cs`: 会话记忆已落盘却**无检索入口** (对位宿主侧 session_search) → 纯 stdlib/零 LLM/确定性打分 (CJK 二元组 + ASCII 词 + IDF + 子串加成), 命中词居中开窗截断; `SessionHistorySearchTests` **10/10** (含负向控制: 无关查询空结果 / IDF 判别力 / **只读保证**: 检索前后 mtime 不变 / 缺文件不抛)。
  - **F2 宣称纠偏**: `skills/critic-rules/SKILL.md` 写的"输出后机器侧静态扫描仍会复核 (双保险)"与代码事实矛盾 (**生产 0 消费**) → 改为真实状态 + 登记"接线"为待办 (诚实优先于好看)。
- **L5 运行级验证 (t8–t12, 用户 5 项计划之一)**: `src/agent.skills/PythonRunVerifier.cs` + `PythonArtifactPlugin` 接线 —— 默认**关** (`AGENTFRAMEWORK_PY_RUN`), 开启后语法通过即真跑并回写 `Ran/RunExitCode/RunElapsedMs/RunTimedOut`; 零 shell (`ArgumentList`), 超时**杀进程树**, 输出上限**排空管道**(否则 300k 输出会假超时), 结构化结果不抛异常。`PythonRunVerifierTests` + 插件接线 **15/15** (含 300k 排空 / 路径含空格与引号 / 闸门关不执行 / 脚本不存在)。
  - **顺带修真缺陷**: 产物命名 `py_<ts>_<sha8>.py` 含时钟 → 同内容跨秒产出两个文件, 破坏"内容寻址幂等"契约 (R368 用例在本机高负载下必红, 属潜伏 flaky) → 改 **纯内容寻址 `py_<sha16>.py`**。
- **L3e 教训表 (exp5 首批, 归属 role 模块)**: `src/agent.roles/` 新增 `LessonGeneralization` (通用化机检: 黑名单词表 + 词法边界, 防误杀) / `LessonTable` (统一记录 + FNV-1a 指纹 + 去重归并 + 版本/增量游标 + STJ 源生成 + 原子写) / `RoleLessons` (role 门面; 无 role 按口径① 不落盘不注入且**显式回报**), 落盘 `data/roles/{roleId}.lessons.json`。`LessonTableTests` **11/11** —— A1 去重计数 / A2 **指纹与独立 Python FNV-1a 实现互锁** / A3 增量游标 / A4+A5① 用户项目目录零新增 / A5② 跨 role 隔离 / A8 正+负 (同通用模式双语实例归并 1 条 Count=2; Pattern 含 `py_compile`/`C#`/`.cs` **一律拒收**)。
- **L4 bge 闲时训练闭环 + 召回实测 (用户本轮新焦点, 关键裁决反转)**:
  - 评测台: 冻结语料 **1299 块/384 文件** + 冻结查询 **120 条** (LLM 生成, 强制不复述片段独特标识符 + ASCII 标识符过滤) + recall@1/5/10/20 + MRR@10 + 词法基线。
  - **实测 (llama.cpp 金标准口径)**: 词法基线 r@1 **0.4417** / r@10 0.750 / MRR 0.5571; **bge-base r@1 0.4417 / r@10 0.7417 / MRR 0.5416**; **bge-small r@1 0.3083 / r@10 0.6333 / MRR 0.4150**。
  - **裁决反转 (诚实更正)**: 10 条硬集上"bge-base 未赢 bge-small"是**样本噪声**; 120 查询口径下 **bge-base 全面领先 bge-small (r@1 +13.3pt)**, 且 ≈ 词法基线 → **纯稠密无优势, 正解是混合检索**。用户钦定基座仍为 bge-small (成本 1/6.6, 内存 106MB vs 193MB), 目标改为"用 T1 适配器把 r@1 从 0.308 逼向 0.44"。
  - **互补性实锤**: bge-small 相对词法 `dense_only_wins=7` / `lexical_only_wins=15` / `both_fail=21`; **union@10 0.7917 (词法单用 0.75, +4.2pt)** / union@20 0.825; oracle@1 **0.5333** (完美选择器上界) → **稠密确有词法够不到的独有命中**, 混合检索有据。
  - 闭环代码: `eval/bge/{bge_lib,collect_pairs,train_adapter,eval_recall,complementarity}.py` (纯 stdlib, 零 shell subprocess, 512 维手写矩阵运算) + `scripts/bge_idle_train.sh` (闲时闸门: load<1.0 ∧ 可用内存≥1.2G ∧ 无在跑任务) + cron `bge-idle-train` (每 30min, 空闲才跑, 无版本产出则零输出不打扰) + 设计文档 exp7。
  - **修缺陷**: ① 缓存 tag 不含模型身份 → 跨模型串用向量 (改 `模型名__前缀_sha_len`); ② llama-server **就绪判定错** (端口可连 ≠ 模型已加载 → qwen3/m3 首请求 503 掉队) → 改为"真发一次嵌入成功才算就绪"。
- **基线**: 单元测试 **772/772** (R368 736) / NativeAOT linux-x64 **0 IL 警告**, `agenthost` **13,792,560 B** (R368 13,775,840 B, +0.12%) / 批测 523 轮 (下轮 524, autopilot 取值自证)。
- **诚实边界**: ① L1 只覆盖已登记项, 覆盖度靠 `covers[]` 机检而非全仓普查; ② L2 的 G1–G9 多数**未接线** (只做组件 + 机检); ③ exp5 前端域登记/`lessons_version` 与三源适配器投影未做; ④ bge 版本小报待首版产出; ⑤ m3/qwen3 召回数字为补跑 (成本维度已淘汰, 不改变选型)。

---

## R368 探索轮: 用户 OOB 5 项计划立项 + PY 落盘/机器校验插件落地 (736/736, AOT 0 IL 警)

- **用户指令 (逐字, 两条)**:
  1. "同步github后继续下轮 并且 新增计划 1.grep本地关键词建索引建立缓存于加载校验能力（需惰性加载）…代码引用索引建立（插件增强服务，需要明确的API规范，要求怎样的数据），全部都建立再一个本质上不主动探索全量（文件索引机制建立插件 返回graph 或 由bge自动建立效果如何？） 2.LLM得到多方案不明确时向用户提出问题menu菜单选择后继续任务… 3. 逻辑校验，修改当前步 看下上一步修改规则对齐当前… 4. agent自动提出需要的工具与工具需求，输入与输出对接参数… 5. 上下文中同类教训/问题记录->应进入教训表…**新增任务全部先列为探索项查找相关数据设计最佳方案后再考虑开发**"
  2. "我需要你对比自身的上下文，并再运行项目agent内 尝试对话 看看再哪个环节 KPI不行，长任务断链，机器验证失败（如PY执行，**你需要自己先内置个PY和先加个PY执行插件**）导致用户某项任务不达预期…着重看看那步应该交给脚本完成agent却又扔给了llm处理"
- **探索产出 (5 路并行只读侦察 + 真机实验 + 本机基准, 未改业务代码)**: [docs/plans/v0.22.0-exploration-index.md](docs/plans/v0.22.0-exploration-index.md) + exp1…exp5 五份独立文档 (含现状事实带行号 / 候选方案对比 / 推荐 / 关键约束 / 验收标准 / 排除项 / 待确认)。
- **关键发现 (5 条, 皆有代码证据)**:
  1. **头号断链: 框架内不存在"生成脚本"能力** — 两条脚本执行链 (skills `scripts/main.py` / `ScriptPluginRunner`) 都要求脚本**已存在于磁盘**; 任何"帮我写个 X"任务只能一段式由 LLM 在回复里吐代码, 不落盘/不执行/不校验/不可迭代。
  2. **"宣称≠实现"再添 3 例** (R365 同类): `OutputCritic`/`CriticPipeline`/`FormatRepairLoop` 已实现但生产 0 调用, 而 `skills/critic-rules/SKILL.md:82` 声称"机器侧静态扫描双保险"; `TaskCharter.AcceptanceCriteria` 0 消费方; CLI `(已路由插件)` 文案无对应校验动作 (**本轮删除该空话**)。
  3. **前端通知层缺失** (探索项 2/5 共用瓶颈): `FormatEvent` 有信封零调用, 域枚举只 3 个, `state.snapshot` 不含 lessons, 无订阅/游标 → "新教训已到达"当前**不可能送达**。
  4. **跨步产物不落不传** (探索项 3/4 同根因): runner 签名忽略上游产物 + 步骤产物不持久化 + 恢复只恢复状态 → 长任务跨步只能靠上下文猜。
  5. **bge 全量索引不可行 (本机实测)**: bge-q8 CPU 单线程 203.5 ms/块 / 4.9 块/s / RSS 306 MB → 全仓 6375 块 ≈ **21.6 min** → 与用户"不主动探索全量"直接冲突。
- **本轮实施 (探索项 4 的 T1/T2/T3)**:
  - `src/agent/registry/PythonArtifactPlugin.cs` (新增): ```` ```python ```` 段 → 落盘 `data/artifacts/py_<sha16>.py` (内容寻址幂等; **R370 修正**: 旧名 `py_<ts>_<sha8>.py` 含时间戳 → 同内容跨秒会写两个文件, 与幂等契约冲突, 本机高负载时用例必红) + 真实 `python3 -m py_compile` 机器校验 + `PythonArtifactLedger` 台账 (线程安全, 单调 Version, 供前端增量读) + telemetry 点 `script_artifact`; **输出恒等** (不改写 LLM 文本/围栏); 非 python 段零损耗透传; `AGENTFRAMEWORK_PY_ARTIFACT=off` 可关。
  - 接线: DI 注册 (`ServiceCollectionExtensions.cs:150-158`) + CLI 步骤 `[05] PY 落盘 + py_compile N/M 通过` (`Program.cs:490-518`)。
  - 零 shell 修复: `PythonScriptValidator` `Arguments` 字符串 → **`ArgumentList`** (跨平台铁律); 新增 `ValidateAsync(path, pythonPath, ct)` 重载使 `AGENTFRAMEWORK_PYTHON` 覆盖真正生效。
  - 测试: `PythonArtifactPluginTests` 6 用例 (好码落盘+过 / 坏码失败不静默 / 非 python 透传零副作用 / 同内容幂等 / 版本单调 / 路由器集成原文还原)。
- **真机对照证据 (同一句话, 同一模型 `deepseek-flash`)**:
  - 改造前: `intent=general`, LLM **1 次** 12990 ms / promptTokens=642, **无文件、无校验**, CLI 显示 `(已路由插件)` 实为空话。
  - 改造后: CLI `[04] 返回区段标记 python` → `[05] PY 落盘 + py_compile 1/1 通过`; 产物 `./data/artifacts/py_20260913_035648_1f3f027c.py` (4573 B / 137 行); telemetry `{"point":"script_artifact","compile_valid":true,"exit":0}`; **独立复核** (不信 agent 自述): 另跑 `python3 -m py_compile` → exit 0 ✓, `ast.parse` 通过。
- **附带修复 (同步上游后发现)**: 同步远端 R366/R367 后全量测试出现 1 例失败 `LlmServiceTests.ConcurrentClients_SpawnOnce`。定位为**真竞态** (非环境噪声): 启动锁只在启动期持有, 抢锁者释放后, 另一客户端到达 `CreateNew` 时见锁已消失 → 判 stale → 重新抢锁并**冗余 spawn** (生产=第二个 daemon 白启后退出码 4; 测试=fakeSpawn 抛"已在运行"致断言崩)。修复: 抢到锁后**再复检一次探针**, 已就绪则释放锁直接复用。复现基线 6 并发 1 失败 → 修复后 **10/10 通过**。
- **基线**: 单元测试 **736/736 全绿** (730 + 6 新增); NativeAOT `linux-x64` **0 IL 警告**, 二进制 **13,775,840 B (13.78 MB)**, 体积同比 +0.18%; **AOT 冒烟真机真 LLM 通过** (`E2E: Success=True` / `Multi-turn round2Success=True` / `full-graph AOT smoke passed`)。
- **诚实边界**: ① 校验仅**语法/编译级** (py_compile), ≠ 逻辑正确, 文档已明写, 不许表述为"已验证可用"; ② 运行级验证 (沙箱+超时+stderr 回灌修复环) **未实现**, 列为 T4/T6 待开发; ③ 探索项 1/2/3/5 全部为**探索态文档**, 未写实现代码; ④ 侦察中的不确定项 (失败簇"超时/停滞"调用点未找到、`CommandWriter` 是否他处接线) 原样保留在各文档 §待确认, 未粉饰。


## R367 v0.21.1 候选 samples WinForms 前端对接 DEMO + FrontendApi 内部问题修复 (提交待 CI 复核)

- **用户指令 (逐字)**: "建立 samples 内创建前端对接 agent.frontendapi 的 UI 项目使用 winform 来做对接 DEMO 查找和继续优化 agent 内部问题"。
- **samples/FrontendApi.WinForms (新增)**: WinForms (`net10.0-windows`) 最小可运行前端, 经 TCP 行 JSON 消费完整 agent 管线。
  - 协议严格对齐实现: 鉴权首行 `{"type":"auth","token":"..."}` / 请求 `{"v":1,"type":"req","req_id","api","payload"}` / 响应回显 req_id / `event` 单向信封 / 错误码 `unknown_api|bad_payload|busy|conflict|not_found|internal`。
  - 功能: `chat.send` (直通 V2 管线) + `state.snapshot` / `state.hello` / `meta.info` / `meta.ping` + **原始协议日志面板** (>> 发送 / << 接收, 排查主手段)。
  - **刻意不入 `agent.sln`**: 仓库 CI 跑 `ubuntu-latest` 且 `dotnet build -warnaserror`; `net10.0-windows` 进 sln 会因 Linux 无 WindowsDesktop 引用包而**构建失败**。仅 Windows 单独 `dotnet run`。
  - 客户端兼容: 旧服务端限流 `req_id` 恒为 `"rate"` 无法关联 → DEMO 退化为"完成最早未决请求", 避免界面永久挂起。
- **本轮揪出的内部问题 (5 项, 前 4 项为真实缺陷, 已修)**:
  1. **限流响应 `req_id` 硬编码 `"rate"`** (真缺陷): 违反契约"响应回显 req_id", 客户端无法关联被限流的请求 (只能靠顺序推测)。→ 改为回显真实 `req_id` (信封非法时用 `"unknown"`); 顺带把限流准入移到解析之后, 非法信封不再白占令牌。
  2. **`chat.send` 缺 `text` 被误判为 `internal`** (真缺陷): `FrontendApiChatRouter` 抛 `BadPayloadException`, 但 `ServeClientAsync` 的 catch-all 把它吞成 `internal`, 与契约已定义的 `bad_payload` 语义不符 (前端无法区分"参数错"与"服务端炸了")。→ 在 `ServeOneLineAsync` 显式捕获并映射 `bad_payload`。
  3. **请求行缓冲 `pending` 无上限** (真缺陷): 客户端持续灌入**不带 `\n`** 的数据 → StringBuilder 无界增长 (内存 DoS)。→ 加 `MaxPendingBytes = 1MB`, 超即断连。
  4. **鉴权握手 `sb` 无上限** (同类缺陷, 更隐蔽): 原 `line.Length > 4096` 检查**只在找到 `\n` 之后**才生效, 未遇换行前可持续增长; 且 auth 阶段位于限流/并发准入**之前**, 5s 窗口内可大量灌入。→ 加 `MaxAuthBytes = 8KB`。
  5. **`meta.info` 版本漂移**: 硬编码 `"0.20.5"` (实际 v0.21.0), 前端无从得知真实版本。→ 校正为 `"0.21.0"` (无单测依赖该字符串; 测试用的是自身 `metaInfo` 注入值)。
- **观察项 (设计如此, 不改)**: ①鉴权失败 = **静默断连** (防枚举探测), 客户端只能靠"首个请求即断连"间接判定 → DEMO 已针对性提示"疑似 token 错误"; ②`FrontendAccessControl` 全局 **10 req/s + 并发 4**, `chat.send` 单次耗时长, 连续发送易触 `busy` → DEMO 提示限流原因。
- **基线**: 现有 `FrontendApiTests` 4 用例 (信封解析 / 真 TCP 往返 req_id 回显 / unknown_api / bad_payload) **均未断言 `"rate"`**, 改动不破坏; 新增代码为纯增量。
- **诚实边界**: 本沙箱无 .NET 10 SDK 且 nuget/builds.dotnet.microsoft.com 被封 → **未本地构建/未跑单测**; WinForms 项目须 Windows 构建, 本沙箱 (Linux) **无法运行验证** (仅源码级对齐实现与契约)。全部改动经人工逐行复核为 AOT 安全增量, 待仓库 CI (build -warnaserror + test + AOT publish) 全量复核后再落版本戳。

## R366 v0.21.1 候选 DeepSeek 内部用例测试 + 推理模型思考链捕获 (提交待 CI 复核)

- **用户指令 (逐字)**: "使用 token 阅读文档后不断完善 click-agent 项目; 内部用例测试用的 deepseek api: sk-…"。
- **DeepSeek 内部用例测试探针 (probes/deepseek-probe, 新增)**: 不依赖 NativeAOT 构建, 用真实 DeepSeek API 验证 `src/agent.modelqueue` 发出的 OpenAI 兼容 chat/completions 请求契约, 并捕获项目 DTO 未解析字段。凭据铁律: key 仅从环境变量 `DEEPSEEK_API_KEY` 读取, 输出脱敏; 内置 1.5s 调用间隔 + 对 401/429/5xx 指数退避重试 (规避 DeepSeek 速率窗口)。
- **推理模型思考链捕获 (v0.21.1 核心)**: 实测证实项目首选 `deepseek-flash` **即推理模型** (返回 `reasoning_content`), 而 `OpenAIChatResponseDtos.cs` 此前未解析该字段 → 思考链整段丢弃。补:
  - `OpenAIChatResponseMessage.ReasoningContent` (`[JsonPropertyName("reasoning_content")]`, 经 `OpenAIChatResponse` source-gen 上下文自动纳入, AOT 安全);
  - `QueueResponse.ReasoningContent` + `CallEntryAsync` 捕获 `choice.Message.ReasoningContent`;
  - `LLMResponse.ReasoningContent` + `ModelQueueAdapter` 透传;
  - 三处 `llm_call` 遥测补 `reasoning_len` (主成功/请求内重试/兜底切换路径一致)。
  - 纯增量, 无反射/无新类型注册, 不破坏 AOT 零 IL 警告契约。
- **models.yaml 校正**: `balance_schemes.deepseek` 旧注 "balance 字段 USD" 实测为 **CNY** (`balance_infos[].currency=C NY` / `total_balance`) → 校正注释; `deepseek-flash` 条目补 "推理模型, 返回 reasoning_content" 说明。
- **实测契约结论 (真实 key, 探针 6 用例)**:
  1. `deepseek-flash` = 项目发送的真实模型名, 接受且返回 `reasoning_content` (推理档 low/high 思考链长度随档增长) ✓;
  2. `deepseek-chat` 非推理, 无 `reasoning_content`; 收 `reasoning_effort` 被无害忽略 (200) ✓ — 项目对全模型透传 `reasoning_effort` 安全;
  3. `deepseek-reasoner` 历史推理模型, 可用性随 DeepSeek 目录变动 (探针保留该用例);
  4. `GET /user/balance` 返回 `balance_infos[].currency=C NY` (非 USD) ✓。
- **观察项 (未改动 auth 语义)**: DeepSeek 对 chat/completions 速率窗口返回 **401 而非 429**; 项目 `OnTransientFailureAsync` 仅把 429 当可重试限流, 401 被当作鉴权硬失败不重试 (真实 401 须 fail-closed, 故不改)。探针已用退避重试规避该窗口。
- **基线**: 真实 DeepSeek 调用 6 用例契约验证通过 (reasoning/reasoner 视目录可用性); 改动 `git diff` 纯增量。
- **诚实边界**: 本沙箱无 .NET 10 SDK 且 nuget/builds.dotnet.microsoft.com 被封 → **未本地跑 730 单测 / NativeAOT 构建 / eval**; 改动经设计评审为 source-gen 安全增量 (仅新增可序列化属性 + 遥测字段), 待仓库 CI (dotnet build + test + AOT publish) 全量复核。版本戳 (csproj 0.21.0→0.21.1 / README 徽章) 待 CI 绿后由统一提交补齐, 避免未构建即改版本号造成口径不一致。

## R365 v0.21.0 Role 系统交付 + 凭据加密 + FrontendApi 鉴权 (批523 13/13, 提交 `7ed4031`)

- **用户指令 (逐字)**: ①"凭据静态加密 请用跨平台统一方案" ②"完善 6 个硬缺口" ③R360 "不做前置人格语料，倾向=对用户问题置信度的赏罚涌现" ④R361 "用对抗用例验证后有效在接近V2 并记得 role 可以外挂依据给 V2" ⑤**R363 "去掉roles目录相关，仅能外部挂载单文件且不可是明文，需压缩友好的快读快写可扩展结构，提供API读取修改写入 并实现 ① 推理中止→失败簇三件实现 ② 赏罚信号接 V2 主链（:1270 替换 llmResponse.Success）"** ⑥"全部提交github，并更新全部文档到当前项目状态"。
- **凭据静态加密 (R358)**: 新建 src/agent/CredentialEncryption.cs — **AES-256-GCM**（跨平台统一原语，AOT 全支持；不用 DPAPI/libsecret 分叉）；master.key 32B 落盘 600 权限；明文自动迁移（Load 兼容 + 首次 Save 即加密）；GCM 篡改拒绝。PromptPersistence 接入；6 单测。
- **Role 单文件 `.rbin` (R363, 用户钦定修订)**: 新建 src/agent.roles/RoleBinaryFile.cs（191 行）— 16B 头（magic `ARBL`+version+flags+压缩长度+原始长度）+ `AES-256-GCM(gzip(JSON))`；密钥=`data/master.key` 持久层级（跨会话可解/换机不可解）；未知 `x:` 前缀键读写往返保留（可扩展）；tmp+rename 原子写；Read/Write API。**目录方案废除**：RoleRegistry.cs 删（照 SkillRegistry 的 roles/ 目录包扫模式终弃），Program `--role` 改接 .rbin 路径、`--roles-dir` 删。实测 700B 文本 → **306B**；hex dump 仅见 magic + 密文（非明文实证）。
- **赏罚涌现倾向 (R360, 用户钦定非前置语料)**: CorrectionDetector.cs 两级判定 — L1 规则词面（"不对/错了/不是这个意思"等强模式，**0 token**，14 轮模拟拦 12/14）+ L2 微 prompt（**单字母 C/A/N 输出协议**，~140 tok/次，均摊 20.7 tok/轮，省 85%）→ RoleGrowthLedger.cs 域级 Beta 计数，confidence=(赏+1)/(总+2)（Laplace），**<0.4 先怀疑 / >0.7 信任 / 样本<5 观察中**。实证：docker 域 5 罚 0 赏 → 0.143 Distrust（"先怀疑"自动涌现）；git 3 赏 0 罚 → 0.800 观察中；跨会话重载保持。
- **推理中止→失败簇 (R364, "三件")**: FailureClusters.cs — 中止检测（超时 / token 超限 / **自证循环**：窗口 3 轮回复 trigram Jaccard ≥0.95 判原地打转）→ 问题指纹簇归类（落盘跨会话）→ **罚分 ≥3 前置注入**策略警告（先澄清/降级/诚实坦白）。Jaccard 修 `last.Count(prev.Contains)` 歧义为 `last.Count(t => prev.Contains(t))`。
- **R365 文档同步期审查（自查发现 3 真缺陷，已修）**: ①**前置注入实际未接线**——`RenderWarning` 有实现但 V2 prompt 组装处从未消费（"三件"只有两件在跑，属宣称与实现不符）→ 接入 Role 块（`message.Content` 指纹命中且罚分≥阈值 → 注入），无 role 时不进分支；②**簇键跨进程不稳定**——`string.GetHashCode()` 在 .NET Core 对 string 每进程随机化种子，落盘的 `failureClusters.json` 重启后键全失配 → "跨会话簇归类"静默失效（同进程测试测不出：`落盘重载_簇保持` 恰好骗过）→ 改 **FNV-1a 32bit 自实现**；③**指纹排序文化相关**——`List<string>.Sort()` 默认文化比较，同问题换 locale 得不同键 → 改 `StringComparer.Ordinal`。新增回归锁 `簇键_进程间稳定`（硬编码 3 键值，期望值由独立 Python FNV 实现交叉验证，非抄实现输出）。
- **赏罚接 V2 主链 (R364)**: CorrectionDetector 后台 Task（不阻塞响应）挂记忆回写区，`GrowthLedger.Record` + LLM 失败 → `FailureClusters.RecordAbort`；L2 判定走模型队列 ContextCompression 通道（微 prompt 隔离）。
- **无 role 门禁 (用户 OOB 校验令)**: 查实 2 处漏洞（纠正检测 Task 无 role 仍起 → 白烧 LLM token；失败簇仍写盘）→ 加门禁：`GrowthLedger == null` 整链失效 — 不起 Task / 不调 LLM / 不写盘 / 联想前置注入关闭（null 安全空返回）；无角色行为与 v0.20.5 一致。
- **对抗验证 (R361)**: /tmp/adversarial 30 例（判罚正例10 / 判赏正例8 / 误杀陷阱7 / 模糊灰区5）；首轮 23/30 → 修 L1 语境豁免（转述/假设/历史）+ L2 单字母协议 + max_tokens 自适应重试（deepseek-flash 是 reasoning 模型，思维链吃光 token 致 content 空）→ **30/30（判分题 25/25 = 100%）**；固化 CorrectionDetectorTests.cs 22 用例（脱 LLM，L1 规则 / L2 mock）。
- **FrontendApi 鉴权 + 限流 (sec2/sec3 部分)**: FrontendAccessControl.cs（共享 token：随机 hex 或 env 注入 / 令牌桶限流 / 并发上限）。
- **真机 E2E**: `agenthost --frontend-api 47819 --role skeptic.rbin` → 同对抗问题回复"前提澄清: 没有证据表明…"（人格从加密单文件加载，4.2s）✓；R355 TCP 47812 chat.send E2E（meta.ping→pong / "回复两个字:收到"→"收到" / 未知 api 结构化错误）。
- **基线**: **730/730 全绿**（729 + 1 新增回归锁 `簇键_进程间稳定`；R362 为 718）；AOT **13.75MB** 零 IL 警告；批 523（DS 主力首测）13/13。
- **诚实边界**: ①R2 能力绑定（Role 绑独立二级召回源）未实施；②`/role` 指令族未做（改 `--role` 启动参数 + `role.info` api）；③embedcpu 无关对 cos 0.90+ vs llama.cpp 金标准 0.18-0.23 差异未解（Q8_0 地板假设已证伪）；④sec2 鉴权仅 token，OAuth/mTLS 未做。

## R355/R356 v0.19.0 FrontendApi chat 域接通 + DS 主力切换 (批 523 13/13, 提交 `3f90e3c`/`6a33404`)

- **用户指令**: ①"若当前你通过API使用LLM服务是GLM请改成DS, ds-flash4.1" ②"② KPI token 口径决策 ③ FrontendApi state.snapshot 真实状态填充"。
- **R355 FrontendApi chat 域**: 新建 FrontendApiChatRouter.cs（chat 域异步 handler 持 IAgent，直通 ProcessAsync）；FrontendApiServer handler 签名升级 `(api, payload)`；Program 加 `--frontend-api <port>` 第三运行形态（TCP 常驻）。两处 AOT/契约级修复：payload 透传缺失（server→router 传 "{}"）、AOT 反射禁用下匿名类型序列化崩溃 → 手写 Utf8JsonWriter。真机 E2E 全通；677/677，AOT 13.4MB。
- **R356 DS 主力切换（二分实证）**: 修前真相 = **首选实为 GLM**（打分 GLM/DS 同 8 分，GLM 价格 0 → fitness×2+推理×3+编码×3-价×2 恒胜；models.yaml "首选"标注仅注释、代码不消费）。修 A：models.yaml 加 `priority`（DS=1/GLM=2），ModelSelectionPolicy 每低一档 **-5 分**压过 0 价优势；性能不敏感分支（压缩/标注）同锁首选；未声明=旧行为不变；6 单测含"未声明时 GLM 仍胜"回归保护。修 B（正名）：**`deepseek-4.1-flash` API 名不存在（400）** → 官方支持名 = **`deepseek-flash`**（另一合法名 deepseek-v4-pro），直调 200 model echo 确认。终验：GLM 坏 key 下 chat.send **一次成功、零 401、零兜底、零 warn**。683/683。
- **R356-b embedcpu 数值审计（llama.cpp 源码对照）**: curl 拉 llama-model.cpp / llama-graph.cpp / src/models/bert.cpp / ggml.c 逐项对照 — 前向 8 项对齐 bert.cpp（gelu=tanh 变体、无 causal mask、scale、残差位置全 ✓）；**修正 pooling：mean→CLS**（BGE 官方 1_Pooling 实证 cls_token + pooling_type=2 是转换器默认值不可信）；WordPiece 去 ▁ 前缀（BERT 词表无 ▁，词="word"/子词="##sub"）→ **相关对 cos 0.8372 → 0.9634** ✓。683/683，推 `a8fe11f`。
- **llama.cpp 金标准对照（决定性实验）**: ghfast 镜像 clone llama.cpp 11s → 构建 llama-server（新版 embedding CLI 已移除，改走 `/v1/embeddings`）→ 同 `bge-q8.gguf` 加载：**mean pooling 无关对 0.17-0.19，CLS pooling 0.18-0.23 vs 我们 0.90+** → **Q8_0 噪声地板假设证伪，前向仍有差异（未解）**；同句前 16 维 cos 0.79。
- **R356-c**: KPI token 口径重锚（tokens_per_case 上界 1300，批 523 实测 1836 带外待定夺）+ state.snapshot 真实状态填充。
- **基线**: 683/683；批 523 = **13/13**，1836 tok/case，8.0s/case（DS 主力首测）。

## R353/R354 v0.20.5 模型通道精简 + bge 本地 CPU 最小推理 + LLamaSharp 全拆 (批520/521/522)

- **用户指令**: ①"去掉项目内本地加载本地llm与官方llm相关功能…仅保留api调用能力" ②"deepseek4.1flash首选 glm5.3flash次选 保留gpt6默认 其余model预留配置移除" ③"去掉llama后仅限cpu 不要onnx 少量代码或成熟库" ④"bge即便用最小实现也请本地cpu异步跑" ⑤"脚本互动若业界无先例则删" ⑥"跨平台vector实现"。
- **通道精简**: 删 LocalLlamaCaller/LocalInferenceAdapter/ILocalInference/OfficialModels/OfficialKeyStore/--official-key; ChannelScheduler 三通道→单 Remote; models.yaml 52→3 (deepseek-4.1-flash 首/glm-5.3-flash 次/gpt-6 默认配置); core.yaml model gpt-4→gpt-6; SkiaSharp 渲染器删 (仅 SVG)。
- **LLamaSharp 全拆** (vendored fork 445MB 目录+nuget 缓存+csproj 引用+native 复制段): BgeEmbedder/SharedEmbedderRegistry/BgeEmbeddingProvider 删; qwen/bge-small-en gguf 删 (bge-q8 保留 — embedcpu 引擎)。
- **embedcpu 新项目** (纯托管零原生依赖, ~470 行): GgufModel (GGUF v3 最小解析+Q8_0/F32 反量化+f16 手写位运算) / WordPieceTokenizer (21128 词表最长匹配+## 子词回退+中文按字) / BgeCpuEmbedder (4 层 BERT forward, TensorPrimitives SIMD, mean-pool+L2, 惰性双检锁, EmbedAsync=Task.Run 异步)。
- **真 bug (R353b 修)**: Q8_0 反量化 Data.ReadByte() 返回无符号 int → 负权重变正大数 → cos 恒 1.0 嵌入无区分度; 修 = (sbyte) 显式转换; 修后与 python 参照逐位一致。
- **R353c 跨平台向量化** (用户检查点): 剩余 4 处标量循环全 TensorPrimitives 化 (embedding 查表/attention 加权/SoftMax/LayerNorm 仿射) — 跨平台自动 SSE/AVX2/AVX512/NEON。
- **R354 eval 同步**: LOCAL_DISABLED 死开关退役 (本地通道本体已删, R107 泄漏源不存在); D4 gate 不再依赖 BGE_MODEL (--embed 走 llm-service), 自动探测 agenthost 路径注入 LLM_SERVICE_BIN。
- **真缺陷 (520/521 双 0/13 负样本如实)**: 清 bin/obj 后未重建 host 而 run_round 用 --no-build → CLI 不存在全 case 650ms 空回; 重建后 CLI 手验 glm-5.3-flash 正常回复。教训: 清 build 产物必须立刻重建 host (run_round --no-build 依赖磁盘二进制)。
- **脚本互动调研归档** (R352-d): 8 家主流 agent 均无"脚本执行中主动问 CLI"先例, 主导模式=单向事件流 → 本项目 ScriptPluginRunner 单向事件流判定保留 (script-interaction-research-R352.md)。
- **基线**: 677/677 绿; AOT 13.4MB 0 IL 警告; bge CPU 热嵌入 ~26-90ms; 验收批 522 (host 重建后)。

---

## R343 v0.20.0 LLM 服务独立进程 — llm-manager / worker 架构 (批516 quick-13 验证中)

- **用户指令**: "将llm服务写成单独进程, 以免新CLI重新加载LLM到显存内, 最好使用小而完善的框架完成"; 纠正 "仅是新增本机 llm host 而非全面修改当前框架llm使用流程"; 钦定策略 "一个是 llm-manager 进程, 一个是实际 llm-service-host; **卸载直接杀 llm-service-host 就好了**"。
- **现状代码事实**: BgeEmbedder (llamalocal) 惰性加载 bge-q8 26MB (加载后 RSS ~157MB 实测), 每 CLI 进程经 DI 新建 (ServiceCollectionExtensions L226); LLamaEmbedder.Dispose() 只释放 Context **不释放 _weights** (LLamaSharp L54-57 实测) → 手工卸载需穿透 SharedEmbedderRegistry (无卸载 API) + 引用计数, 复杂易漏; CLI 生命周期 = REPL while(true) (L296) 或 -q 单次, 多实例并存。
- **架构**: `llm-manager` (轻量常驻, 0 模型, 不随 CLI 生死) 对外 UDS 透明代理 → lazy spawn `llm-service-host` worker (真 bge); 卸载 = kill worker (OS 回收全部 native 内存, 绕开手工释放/引用计数)。ping 由 manager 直答 (探活不触发加载); 双启保护 .manager.pid/.worker.pid; 客户端 .startlock 原子抢占; SIGKILL 后孤儿 worker 由新 manager 清理。
- **卸载判定 (纯函数, 单测矩阵)**: `ShouldUnload = workerUp ∧ inflight==0 ∧ availMb>0 ∧ availMb<floor(512) ∧ cliCount==0` — **不按时间** (用户钦定: 内存充足常驻); **空闲长连接不阻止卸载** (实测缺陷修正: 原含 conns==0 导致 CLI 长连接永久阻止卸载); 读不到内存 (非 Linux) 保守不卸。
- **跨平台 (用户 OOB "/bin/sh 跨平台怎么办?")**: 产品代码零 shell — spawn 用 `Process.Start`+`ArgumentList`, 卸载用 `Process.Kill(entireProcessTree:true)`, 存活判断 `Process.GetProcessById`+`HasExited`; daemon 自写日志 (env LOG, 替代 sh 重定向); UDS 跨平台 (Win10+ AF_UNIX); /proc/meminfo 非 Linux 优雅降级 (Windows GlobalMemoryStatusEx 待办)。
- **验收**: 新增 LlmServiceTests(9)+LlmManagerTests(7) → **全量 661/661 绿**; AOT publish 13.6MB **0 IL 警告**; 真机 E2E: ①manager READY 0 模型 → ②首请求 lazy worker (RSS 157684KB, bge 512 维) → ③kill -9 worker → ④下请求自动重拉 (pid 2659546→2659594) + manager 存活 → ⑤阈值拉满+无 CLI 实例 → worker 被卸载无残留。
- **诚实边界**: ①RemoteEmbedder 尚无框架内调用点 (opt-in 集成 = v0.20.1 P4-a); ②worker 仅服务 bge embed, 本地 LLM 推理未 worker 化 (P4-b 评估); ③Windows 内存探测未实现。

## R338 v0.17.3 P10 锚词 Span 化收尾 (批288 quick-13 13/13)

- **立项**: improvements.md 下轮候选 — R333 (v0.16.4) 完成 P10 中文 2/3/4 字窗 long-key 零分配后遗留 **English 段未动** (function-map-R326 P10: 压缩热路径锚词提取)。可选性: c 收口/dormant 退役均需用户裁定 → 本轮唯一可执行候选。
- **现状代码事实** (src/agent/contextassembler/ContextAssembler.cs, ExtractAnchorWords L1006+): CJK 窗 R333 已零分配; English 段仍 `Regex.Matches(content, "[A-Za-z]{3,}")` + 每匹配 `m.Value.ToLowerInvariant()` = **每 English 词 2 次短串分配 + MatchCollection/Match 分配**; 压缩热路径每超限 snippet 触发一次 (代码/英文片段词数×2 分配)。
- **修法**: English 提取 → `Regex.EnumerateMatches(content.AsSpan())` (零 Match 对象) + **≤7 字符词 8bit/char long 键零分配计数** (ASCII 字母 `|0x20` 即小写; 8×7=56bit 键域无歧义; 字母编码无中间零字节 → decode 移位归零即末字节; 复用栈槽免 CA2014); >7 字符词 string 兜底 (长词稀有); 两路 distinct 首见登记 enOrder (枚举序=match 序=内容首见序), 计数毕按登记序解码 count≥2 候选入 words — 与原实现 (English match 序先、CJK len-major 后) **同插入序**, count 相同下稳定排序输出全等。
- **验收**: **624 单测绿** (+5 ExtractAnchorWordsEquivalence InlineData: R333 随机语料英文词全 ≤7 字符未覆盖 >7 兜底路径 — 补 >7 重复/短长混合首见序/7-8 边界同 count 保序/>7 大小写折叠/7 大写折叠×8 string 交替); AOT publish agenthost 13.5MB **0 IL 警告** (仅预存在 CS0649/CS0169/xUnit1030); 批288 (round 515) quick-13 **13/13** tok/case 1806 (KPI_BREACH 带外 — C19 重案 8023 tok 已知方差同 R337/R331 判型, 通过率主口径零回归; 改动为压缩路径纯函数不进 LLM 链)。
- 收益: English 主路径 (≤7 词, 绝大多数) 每匹配 2 短串+MatchCollection → **零分配**; >7 仅兜底; 与 R333 CJK 段合拢 P10 "单遍扫描 + Span/字典" 全部建议。
- 诚实边界: 片段级锚词缓存 (function-map P10 建议) 未做 (收益需跨 snippet 重复片段真实命中分布, 候选中); >7 词每 occ 仍 Substring+ToLower 与旧版同 (未回退)。
- 下轮候选: c 收口 (/schedule 持久化 + 外部 cron 挂钩 + 定时 skill — 需用户裁定) / 片段锚词缓存 (需命中分布) / RAGConfig 内联 hash 收敛 (需加 rag→vectormemory 引用) / dormant 退役 (需裁定)。

## R337 v0.17.2-b/c 脚本插件协议 + 条件定时 (批287 quick-13 13/13)

- **立项**: 用户钦定 (执行层自需脚本一律 py 编写 → CLI 验证 py 正确后交插件服务执行; 明确对接协议: 定期反馈/结束前返回/长执行心跳) + plan docs/plans/v0.17.2-activity-script-plan.md §2/§3 (b 脚本插件协议 + c 条件定时, 依赖 a 的 IsOtherAgentBusy 条件原语)。
- **协议层** (src/agent.skills/): ScriptPluginProtocol.cs — **JSON Lines 事件流** `{"type":progress|checkpoint|heartbeat|done|error,"ts","msg","data"}`; done/error=权威终态 (以事件为准, 进程退出码仅兜底); done 回填 summary + data.outputs(产物路径); 非 JSON/未知 type 行=调试噪声 (忽略计数); ts 容忍 epoch 秒/毫秒; ScriptEventStreamParser 状态机 (时钟注入): 事件驱动活性 → >2×heartbeat 无事件=疑似挂起判定。PythonScriptValidator.cs — **py_compile 验证门** (真实 `python3 -m py_compile`, 进程级 AOT 安全): 失败=拒绝执行 + 教训 `script-invalid:<name>` (ExecutorLessonMemory 频率加权)。
- **执行器**: ScriptPluginRunner.cs — 验证通过 → task-json 落盘 data/script-plugin/tasks/ (源生 STJ 序列化, 用后即删) → `python3 script --task-json <file> --heartbeat-secs N` (PYTHONUNBUFFERED 强制流式) → 事件流消费 → 活性监控 (疑似挂起打点一次不杀) → 总超时杀进程树返回失败 → 进度/心跳计数打点 + 结束回填。条件定时: ConditionalScriptScheduler.cs (v0.17.2-c) — "如果当前没有其他任务存在则 XX 后执行 Y": 延时到期 → 轮询其他 agent 忙 (接线方注入, 默认 ActivityService.IsOtherAgentBusy 自身排除) → 空闲即执行/忙重试至 give-up; 重试/放弃窗口全走配置委托, 延时/时钟可注入。
- **接线**: /schedule-run <延时秒> <py路径> [目标描述] 本地指令 (LocalCommandRouter + V2 特判臂 0ms 拦截, 坏 py 拒绝+教训落盘 ExecutorLessonMemory.Default; v1 延时上限 60s)。
- 验收: **619 单测绿** (+18 ScriptPluginTests: 解析终态/噪声容忍/秒容忍/挂起活性重置/真实 py_compile 好坏/真实 python3 子进程 done 回填+error 权威+协议违例+静默超时挂起观测+坏 py 真实教训 store 落盘/条件调度 空闲执行·忙拒绝·验证拒绝·取消 — 注 R336 文档 597 为其时计数口径, 含 Theory 行差异); AOT publish 0 IL 警告 (仅预存在 NU1510 包引用提示); **E2E 真机 AOT host 双场景**: /schedule-run 0 好脚本 → ✅ 完成 (200ms 事件3 心跳1, 产物回填 data/script-plugin/outputs/) / 坏 py → ⛔ 拒绝未执行 + `script-invalid:e2e_bad.py` 教训真实落盘; 批287 (round 514) quick-13 **13/13** tok/case 1641 (低于近4轮 1672-1811, KPI_BREACH 带外系 C19 重案 7680 tok + LLM 方差已知现象, 通过率主口径零回归 — 本改动为惰性本地指令+未触发库, 不进 LLM 链)。
- 诚实边界: /schedule-run 为轮内阻塞式 ≤60s v1 (长延时交互语义、跨重启持久化、Hermes cron 挂钩、定时任务 skill 面 = 下轮候选, 交互语义待用户裁定); 脚本产物默认写 data/script-plugin/outputs (改用户文件走 v0.17.1 staging 属接线方职责, 本期未接)。
- 下轮: c 收口 (/schedule 指令面持久化 + 外部 cron 挂钩 + 定时 skill) / P10 锚词 Span 化 / dormant 退役 (需用户裁定)。

## R336 v0.17.2-a 活动任务注册表 (批286 quick-13 13/13)

- **立项**: 用户钦定 (获得所有激活窗口活动任务/其他 CLI 状态/job_id 通知/"无其他任务则 X 后执行"原语) + plan docs/plans/v0.17.2-activity-script-plan.md (a 活动注册表 / b 脚本插件协议 / c 定时 skill 分期)。
- **ActivityService** (src/agent/activity/): 每活动 CLI 进程心跳文件 data/activity/<pid>.json (AtomicFileWriter; 退出 finally ClearActivity + 崩溃由 TTL 兜底); 条目含 pid/window(env AGENTFRAMEWORK_WINDOW)/job_id(env AGENTFRAMEWORK_JOB_ID)/agent/任务摘要/心跳; 查询扫目录; 过期 TTL **90s** (E2E 实证教训: 心跳为轮级非定时器, LLM 单轮 30-60s, 10s TTL 误清在跑实例); IsOtherAgentBusy(自身排除) = "无其他任务" 条件原语。
- **接线**: V2 OnProcessAsync 轮首 Heartbeat(message.Content); Program.cs finally ClearActivity (守护轮并行补); /activity 指令 (Known+switch 臂+V2 特判 0ms 渲染列全部激活 agent: pid/win/job/status/心跳龄/任务)。
- 验收: **597 单测绿** (+6 ActivityService: 注册查询/过期清理/自身排除/多实例无串扰/渲染含 job_id/损坏容忍); AOT 0 IL 警告; **E2E 双实例真机**: 实例 A (win-A/job-A-test/长任务) 运行中 → 实例 B /activity 看到 A: pid/win=win-A/job=job-A-test/任务摘要 ✓ (首版失败=TTL 10s 误清, 改 90s 复绿); 批286 (round 513) quick-13 13/13 tok/case 1811。
- 下轮: v0.17.2-b 脚本插件协议 (py 验证→插件服务执行, JSON Lines 事件流/heartbeat/done 约定) + c 条件定时 (IsOtherAgentBusy 已就绪)。

## R335 v0.17.1 离线变更 + 用户审批 (批285 quick-13 13/13)

- **立项**: 用户钦定 (Q1-Q7: CLI 产出需审批/VS Code 编辑保护/不能停/落盘不占真实地址/下次打开恢复/过期周期/前端取得/多批合并) + plan docs/plans/v0.17.1-staged-approval-plan.md (逐问题设计)。
- **存储**: src/agent/staging/ — StagedFileStore (批次 content 原样落 data/staged/<batch>/<n>.content **不占用真实文件地址**; index.json 原子写; 恢复=新实例读 index; 过期三阶段 TTL→expired(内容保留可取回)/TTL×2→reclaimable/显式 cleanup 物理删 — 不静默丢); ChangeBatch/StagedItem (基线 sha256 快照模型); StagingSha (IncrementalHash AOT)。
- **审批**: ApprovalController.Apply = LockedFileWriter.WriteIf **锁内基线比对** — 用户/编辑器在批次创建后改过目标 → 冲突拒绝绝不覆盖 (Q1 VS Code 场景机械保证); 多批 approve all 按创建序, 后批基线过期 → partial 报告人工; 冲突教训入 ExecutorLessonMemory (staging-conflict:<file> 频率加权)。
- **指令**: /staged [--json] /staged diff <id> /approve <id|all> /reject <id> /cleanup (Known+switch 臂+V2 特判渲染 0ms 本地拦截, /skills 族同款); --json 单行输出供前端 (Q5: 状态文件 data/staged/index.json 也可直读)。
- **验收**: **591 单测绿** (+10 StagedApproval: staging 落盘不占真实地址/恢复/apply 成功/用户编辑冲突拒绝/新建语义/多批顺序+冲突/reject/过期三阶段/--json/损坏容忍); AOT 0 IL 警告; **E2E 三场景真机** (AOT host): /staged+diff 查询 ✓ → 模拟 VS Code 编辑 → /approve ⚠冲突未覆盖 (文件保持 USER-EDITED-IN-VSCODE) ✓ → 恢复基线 → /approve ✓已应用 1 项 (AGENT-PRODUCED-CONTENT 落盘); 批285 (round 512) quick-13 13/13 tok/case 1765。
- 下轮: v0.17.2 窗口&任务感知 (OOB 钦定) + 脚本增强计划 (OOB 钦定)。

## R334 v0.17.0 执行层稳固化 T1-T4 (批284 quick-13 13/13)

- **立项**: 用户钦定 (2 agent 同时写 1 文件族问题 → 工业化 IO 防御) + plan docs/plans/v0.17.0-executor-hardening-plan.md。
- **T1 跨进程锁**: src/agent/execution/FileLocking.cs — FileLock (.lock 文件 FileShare.None=Unix flock LOCK_EX, 持有者崩溃内核自动放锁, 锁文件含 pid); AtomicFileWriter (tmp+Flush(true)+Move overwrite 原子); 删除竞态防护 (释放后校验锁文件仍属自己 pid 才删)。
- **T2 占用者检测**: OccupantDetector — 快路径读锁文件 pid; 主路径 /proc/locks (解析实证 Linux 6.8: "1: FLOCK ADVISORY WRITE <pid> <dev>:<inode> 0 EOF", pid 是含 inode 段前一项, 非固定 index); stale 判定 /proc/<pid> 不存在。
- **T3 教训临时记忆**: ExecutorLessonMemory — 失败→原因→临时记忆, **频率加权增长** (count1 摘要/count≥3 补方案/count≥8 补上下文), 24h 降级 7d 移除 (时钟注入), 手写 JSON 持久化原子写 (踩坑: JsonEncodedText.ToString 带引号致双引号 JSON → 手写 Esc; Save 拼接缺引号 → Esc 包引号)。
- **T4 接入**: TaskCharter.Save → WriteIf (同 Id 状态推进覆盖/异 Id 让位 — KeepExisting 会让 TaskCharterTests 失败: 自身 planning→done 被挡, 教训=自身生命周期推进 ≠ 异主冲突); GuardrailMemory.Save → 加锁 Overwrite; 冲突结构化 + Record 教训 + executor_write/executor_lesson 打点。LockedFileWriter.WriteIf (锁内条件覆盖, 无 TOCTOU)。
- **设计踩坑 (FileShare)**: FileShare.Read 实测同进程第二 Open ReadWrite 仍成功 (不互斥, 测试实证) → 必须 FileShare.None; FileOptions.DeleteOnClose Unix=打开即 unlink → 破坏锁文件可见性。
- 验收: **581 单测绿** (+11 ExecutorHardening: 双锁互斥/stale 接管/活锁不误删/占用者报告/原子写无残留/KeepExisting 让位/教训频率升级衰减/持久化往返/损坏容忍/8线程120行并发追加零丢失); AOT publish 0 IL 警告; 双进程 flock 竞争 smoke (60/60 全成功零交错 — smoke 判定假警报已诊: split 后段天然无分隔符); 批284 (round 511) quick-13 13/13 tok/case 1672。
- 下轮: v0.17.1 离线变更+用户审批 (OOB 钦定, plan 已建 docs/plans/v0.17.1-staged-approval-plan.md)。

## R333 v0.16.4 P10 锚词提取 long-key 零分配 (批283 quick-13 13/13)

- **现状**: ExtractAnchorWords (ContextAssembler.cs L1000) 中文 2/3/4 字全滑窗每位置 3 次 Substring 短串分配 — 压缩热路径 (每超限 snippet 一次, 大片段 ~65K CJK chars → ~200K 分配/片段)。
- **修法**: CJK 全在 BMP (UTF-16 单单元 ≤0xFFFF) → 窗口编码 long key (每 char 16bit 顺序拼, 低位=窗首; 起点必 CJK 使高 16bit 非零、每 len 独立字典 → 键域无歧义) 零分配计数; 仅 count≥2 候选解码 string (AddDecoded 固定 len 正向移位)。
- **语义等价证明**: ExtractAnchorWordsEquivalenceTests 10 测 — 反射调 private 新实现 vs 内联旧 Substring 算法: 6 已知样本 + **40 轮随机混合语料 (CJK/ASCII/标点/emoji/超长词) 全等**。中途设计漏洞自捕: while(k!=0) 解码无法定 len + 低位反序 → 改 3 独立字典分 len。
- 验收: **570 单测绿** (+10); AOT publish 0 错误 0 IL 警告; 批283 (round 510) quick-13 13/13 tok/case 1712 (vs R331 1875 / R332 1889 — 更低, C19 重案方差内; pass-rate 主判据干净)。

## R332 eval per-case isolation hardening (批282 quick-13 13/13)

- **根因**: run_round.py 清理只在轮级 (R81), case N 落盘会话记忆 (data/sessions/cli-*_memory.json, CLI 每进程读+追加写) + RAG index 泄入 case N+1 新子进程 → C14 isolated=None 两次 12/13 flake (rounds 506/506b; R331 A/B: 同 binary standalone 2/2 PASS + OLD 13/13 PASS, 失败仅现整批窗口 = cross-case leakage 时序累积)。
- **修法**: case 循环内每 case 前清 sessions + RAG 落盘 (setup 键仅 charter/guardrails 且 fixture 在 run_case_with_setup 内应用 → 清理先于 setup 安全; repl 型 case 内部多轮共享进程状态不受影响)。
- **教训 (执行层)**: execute_code 内 Popen 起批测会被 cell 300s timeout kill 连坐 (半批 16/16 PASS 无汇总即死) → 长批必须 terminal background=true + notify。
- 验收: 批282 (round 509) quick-13 **13/13** (tok/case 1889 vs R331 1875 同水平; C14 PASS); 508 半批 16/16 (被连坐前)。AOT 无需重发 (eval 层改动)。下轮候选: P10 锚词 Span 化 / RAGConfig 内联 hash 收敛 / dormant 退役 (需裁定)。

## R331 v0.16.3 RAG 落盘裁剪摊销 (P12, 轮507 13/13 验收)

- **背景**: function-map-R326 P12 — RAGConfig.PersistDocument (L231-262) 每 append 后无条件 `File.ReadAllLines` 判 512 行裁剪, 超限 `WriteAllLines(lines[^512..])` → 库过 512 后**每消息整读+整写** (~512 行恒定浪费 O(库大小) 文件 IO); 增长期 1→512 每 append O(n) 读 = O(n²) 累计。每用户消息热路径 (对话库逐轮涨)。
- **改动**: 常量抽取 `RagPersistMaxLines=512`/`RagPruneInterval=64`; `Interlocked` 计数 `_persistAppendsSincePrune`, 仅每 64 次追加整读一次判裁剪, 超限重建保留最新 512 (`lines[^512..]` 语义不变)。文件瞬时上限 512+63 行 (有界松弛), 每次裁剪终态与逐次裁剪内容集一致 (追加+保尾裁剪单调); 文件被外部删除/重建后计数器最多漂 64 次 append, 下次裁剪整读实测自愈。
- **验收**: **560 单测绿** (+3 RagPruneAmortizeTests: 700 文档 → 文件行数 ∈(512,575] 且保最新裁最老 / 新实例重载只恢复幸存者+追加继续正常 / 小库 50 行零裁剪); AOT publish 13.2MB **0 IL 警告** + CLI 冒烟; 批测轮 507 quick-13 **13/13 零回归** (tok/case 1875 超旧健康带 = C19 8523 级重案 + LLM 方差, R329/R330 同判型; 通过率主口径零回归)。
- **C14 整批 flake 调查 (非本改动引入, 留档)**: 轮 506/506b 均 C14 isolated=None FAIL (12/13, tokens≈1000=未 spawn 隔离链); 同代码单跑 C14 ×2 PASS (isolated=True score=2) + 轮 507 整批 C14 PASS + 旧代码 86a4f13 A/B 整批 (506old) 13/13 C14 PASS → 失败集中于 05:00-05:15 窗口, 与代码无关。归因: TopicRelevanceEvaluator 是确定性规则器 (R308), C14 方差来自**输入**: turn1 锚/goal 的 LLM 提取质量 + **跨用例 tendency/画像泄漏** (run_round R81 只轮级清 RAG+会话记忆, case 进程共享 tendency 文件 → 前序 C07/C13 输出随 LLM 方差变化, 泄漏进 C14 锚提取 → 弱锚/无锚路径不隔离; 失败回复实测引用前序用例 "Web API 项目/代码推送" 上下文坐实泄漏)。→ 下轮候选: eval 隔离按 case 清理 tendency/画像状态 (harness 硬化)。
- 收益: 库过 512 后每消息文件 IO 整读+整写 → 每 64 消息一次 (64× 摊还); 增长期读 O(n²)→O(n)。
- 下轮候选: P10 锚词 Span 化 / C14-in-batch 隔离硬化 (eval 按 case 清 tendency) / RAGConfig 内联 hash 收敛 (需加 rag→vectormemory 引用) / P4 二段-前缀否定 (需真实命中分布数据) / dormant 退役 (需用户裁定)。

## R330 v0.16.2 工作区召回流式化 + 整轮字节预算 (P4 首段, 批282 13/13)

- **背景**: function-map-R326 §4.1 P4 — ContextAssembler.RecallFromWorkspaceAsync 每文件 `ReadAllTextAsync` 整读 (≤200KB/文件 × ≤300 文件 → 单轮理论最多 ~60MB 文本读入 + `Split('\n')` 全行数组数千短 string 分配/文件), 无整轮读取预算; 文件/编码类意图每装配触发 (recall_workspace 打点监控), 中热。
- **V1 流式化**: 整读+Split → `StreamReader` 逐行 (`FindKeywordLineRankedStreamingAsync`), 峰值内存 = 单行。**语义与字符串版完全一致 — 无前缀截断, 文件尾部命中不丢** (35KB 深处命中单测锚, 前缀否定需真实命中分布数据, 未做, 候选); 单行命中计数抽 `CountKeywordHitsInLine` 双版共享防漂移 (FindKeywordLineRanked 字符串版保留, WorkspaceRelevanceTests 反射锚)。
- **V2 预算化**: 满分档 (5 hits) 命中即停读 (原整读后 break 无 IO 收益); 整轮字节预算 `WorkspaceRecallBytesBudget`=4MB (static 非 readonly — 单测反射注入小预算验证截断路径), 超预算停止扫描剩余文件 — 与 Take(300) 同哲学 (按修改时间降序, 丢最旧文件; R30 已声明"扫描窗口内召回质量"边界); 空文件跳过。
- **验收**: 557 单测绿 (+4 WorkspaceRecallBudgetTests: 文件尾部 ~35KB 关键词命中不丢 / 预算 2KB 截断只留最新文件 / >200KB 大文件跳过 / 多词最佳行 R118 相关分语义); AOT publish 13.2MB **0 IL 警告** + CLI 启动冒烟; 批测 505 quick-13 **13/13 零回归** (tok/case 2004 超旧健康带 = C19 8523/C14 4291/C13 2616 重案 + LLM 方差, 同 R329 判型 — 通过率主口径零回归, hash/bge 路径不受影响)。
- 收益: 工作区召回峰值内存 整文件→单行 (大文件数千行数组分配消除); 单轮读取上限 理论 ~60MB → 4MB 预算窗口。
- 下轮候选: P10 锚词 Span 化 / P12 RAG 裁剪 O(n)→摊还 / RAGConfig 内联 hash 收敛 (需加 rag→vectormemory 引用) / P4 二段-前缀否定 (需真实工作区命中分布数据) / dormant 退役 (需用户裁定)。

## R329 v0.16.1 HashEmbeddingProvider 双实现统一 (T-B4 遗留收口, 批281 13/13)

- **背景**: v0.15.3 计划 T-B4 遗留 — 三份 hash 语义并存: vectormemory 384 英文版 (EmbeddingProvider.cs) / llamalocal **256 硬编码版** (EmbeddingRouter.cs, bge 缺失兜底) / RAGConfig 内联 (RecallRateTests 锁定, 不动)。两 class 注释均自称 "R58 语义" 但实现矛盾 (256 vs 384 维度分裂、英文-only vs 中文标点、单桶覆盖 vs 3-seed 摊开)。
- **V1**: vectormemory.HashEmbeddingProvider 升级为统一唯一实现 — RAGConfig.Tokenize 同族分词 (lower + ASCII 标点全切 + ascii↔非ascii 边界切 R44 中英混写 + 中文 2-gram 滑窗 R6) + 3-seed 摊开桶分配, dim 可配默认 **384**; 不做预归一化 (全部调用方 CosineSimilarity 自归一, 与 RAGConfig 内联一致)。
- **V2**: llamalocal.HashEmbeddingProvider (256) **删除**; EmbeddingRouter fallback → vectormemory 统一版 (384)。grep 全仓无残留。
- **验收**: 553 单测绿 (+5: 维度 384/中文多桶/R44 混写召回/R6 无空格召回/EmbeddingRouter fallback 指向统一版); AOT publish 13.2MB **0 IL 警告** + 冒烟; 批测 504 quick-13 **13/13 零回归** (tok/case 1877 超旧健康带系 C19 重案 8877 + LLM 方差, 逐案对比 C03 -1076/C13 +1199/C19 +1563, hash 路径批测不参与, 非本改动引入; 批279 1687 亦在旧带外 R322 已知)。
- 收益: 降级/AOT 形态 RAG 与记忆整合向量空间统一 (384), 中文召回从整句 1 桶升级为 2-gram + 边界切 (R6/R44 语义覆盖)。
- 下轮候选: P4 工作区召回预算化 / P10 锚词 Span 化 / P12 RAG 裁剪 O(n)→摊还 / RAGConfig 内联 hash 收敛 (需加 rag→vectormemory 引用) / dormant 退役 (需用户裁定)。

## R328 v0.16.0 skills 引擎完整落地 (批280 37/37 验收)

- **CLI 外挂 skills** (用户钦定 v0.16.0-a): `--skills-dir <目录>`(可多次)/`--skills-blacklist <id或目录名>`(可多次)/`--skills-file <单SKILL.md>`(可多次) → env 钩子传 DI → ServiceCollectionExtensions 合并注册; 外挂同 SkillId 覆盖内置 (Register 字典后写胜); RemoveById 精确 id+包目录名双匹配。E2E: 外挂 my-ext-skill 进注册表 (7 个激活)。
- **运行时动态过滤** (v0.16.0-b): SkillRegistry.SetActiveWhitelist/Blacklist (volatile HashSet, All getter 应用, null=清除) — 循环任务内动态指定可匹配范围。
- **/skills 指令族** (v0.16.0-c): /skills 查询当前激活 (id/版本/类型/触发词)、/skills-only /skills-exclude 动态过滤 — Known+TryRoute switch 三臂+V2 特判渲染 (Dispatcher.Registry 只读暴露)。**根因教训: Known 集合加了但 switch 臂没加 → 落 _ => NotCommand 送 LLM (模型幻觉能力表); SkillsCommandRouteTests 测试先行逮住**。
- **skills 格式统一**: 6 包全部规范 frontmatter (name/description/version/type/keywords; image-gen 补缺失→knowledge_hint; normative 显式化)。
- **critic-rules 语言无关化 2.0.0**: R01-R08 按语义定义 (堆分配/串拼接/async void/阻塞/吞异常/判空/浮点比较/资源释放) + C#/Python/Go/Rust/Java 映射; config 同步去 domains:[csharp]。
- 验收: **548 单测绿** (+SkillsCommandRouteTests 2); 批280 全量 37/37 (mass 503, tok/case 2075 = 全量口径含 C19/C16 重案+诱饵族, 非回归); AOT publish 0 错误。撞号险情 1 次 (误取 502 与批279 冲突, R257 协议 30s 内 kill 换 503, 旧文件零损失)。
- 下轮候选: R-3 HashEmbeddingProvider 双实现统一 / P4 工作区召回预算化 / P10 锚词 Span 化 / P12 RAG 裁剪 O(n)→摊还 / dormant 退役决策 (需用户裁定)。

## v0.13.x (2026-09-08~09) — 底座能力与收敛环 (已落地, R205-R288)

### 主题 (用户钦定): 渐进式探索 / 思考链收敛 / 兜底粘性路由 / 格式修复收敛环 / 底座能力长期观察

### ✅ 完成记录 (真实执行)

**v0.14.0 输出侧经验闭环 + v0.15.1 任务路由 (R318-R322, 2026-09-09)**
- OutputCritic (R318): 8 条 C# 反模式静态规则, 14 测; plan 三版演进 (孤立设计→用户纠正"回顾既有牵引体系"→master-plan S/M/D 盘点+第四环定位)
- SelfCritic (R319, 用户钦定方向): LLM 自审=人类经验检索 (常见反模式分布内可靠); 三失效模式 (过度批评/幻觉批评/分布外) 对策=逐字子串锚+机制解释强制+Anchor 过滤; 单源自评绝不直接进生成上下文
- FixMemory (R319): 修法记忆 (反模式→修法), 来源秩 human_review > metric_delta > llm_self_confirmed; R0071 误信全仓清零 (用户纠正: 非本项目编号)
- CriticPipeline (T2c): 静态=确认态 / LLM 交叉=去重 / LLM 单源=观察态不入上下文
- T2d 接线: DataSourceType.FixMemory + ContextAssembler 分支 + K1 全隔离剔除 (R302 对齐); 装配接线 3 次插错教训=多块编辑用 git diff 不做行号算术
- TaskCharter (R322, v0.15.1-a): 章程 schema + 任务进行中新输入三态路由 (supplement→pending / pivot→归档 failed / isolate→既有链); E2E 三态实证 + 归档快照修正 (Archive 先 Save 终态再 Move)
- 数据: 批263-265 全绿 (12/12 quick-12); 538 单测

**v0.13.3 牵引收口与重构事故自捕 (R309-R313, 2026-09-09)**
- 缺陷 72 修复 (R309): executive 直达补 intent 打点 (C04/C06 intent=general 复现; llm_calls=0 保留=executive 本质无 LLM); init 键教训第 3 次 (R142/R151/R309) — topic_* 键加错 init dict, 批254 KeyError 杀批
- 牵引阈值 env 化 (R309): AGENTFRAMEWORK_TOPIC_STEER_THRESHOLD (默认 2)
- explore 执行方式修复 (R310): AOT apphost framework-dependent 无 DOTNET_ROOT 秒退假跑 → dotnet dll 对齐 run_round; 24 案真跑 A 0.167/B 0.722 (+56pt 历史最高); B 轮 3 viol 定性=must_not_contain 与引用来源的判定张力
- 否定围栏双向化 (R311): 前 40ch + 后 20ch (后置否定 "并非光合作用" 兜住); 3 形态离线验证; 批256 负样本零回归
- 无锚轮词面 verdict (R312): R308b 删词面退路致无锚会话牵引失效 → else 分支纯词面模式; 但**重构事故**: 有锚隔离执行链误删 → 批257 C14 首败 (isolated=None) 实锤 → R313 恢复
- 衔接副词精修 (R313): "再讲 X" 单字"再"误判指代 → 裸衔接词 + 无复合指代在场 + 词面偏离成立 → veto 不适用; 💡 提示链恢复 (SteerHint ×2)
- 欠账补齐 (用户点名): 批 188-217/218-247 两段归档 (R312), archive-first-then-retire 制度
- 数据: 批255 11/11 1228/case; 批256 11/11 1161/case; 批258 11/11 1003/case (C14 复绿)

**v0.13.3 合并判定与复查收口 (R307-R308, 2026-09-09)**
- L1 轻牵引 (R307): 连续偏题 ≥2 轮 → 回复尾追加衔接提示 (答案本体零改动); 追加位置必须在区段路由**之后** (ProcessAsync 会重写 Content — E2E 实证)
- TopicRelevanceEvaluator (R308): 隔离+牵引合并判定 API — 一份 verdict 三路消费 (Isolate→subagent / SteerHint→牵引 / Normal); 分级 veto (指代词绝对 / 短询问在实体非零重叠时)
- 复查三轮 (用户钦定): ①首查 4 缺口 (隔离点直调 Check / steering 独立打点 / verdict 双算 / 旧注释) ②二查 3 缺口 (run_round 零消费 topic_relevance / K1 双开关语义 / no-anchor 观测盲区) ③三查围栏双脚本同源 — explore_eval 窗口 20→40ch + 词表补 "不能" (TC-F06 离线双向 4/4) + suspect 降级语义统一
- **缺陷 72**: skill executive 直达路径 (L481 early-return) 绕过 LLM 后全部打点 — C04/C06 llm_calls=0 结构性根因 (批244 起即如此, 此前误标瞬态)
- 数据: 批250 11/11 1172/case; 批253 11/11 1061/case; 499 单测; 探索增益口径澄清 (R288 可达 11 案 +18pt / R289 全 24 案 +39pt, README 用后者)

**v0.13.3 宿主执行与真机 E2E (R272-R288, 2026-09-09)**
- 思考链宿主执行全线打通 (R286): HostExploreExecutor (URL GET digest/页内链接发现≤5/目录文件路径穿越防护) + V2 RunThinkChainAsync (播种→4s/4步→首败即停→回注); 真机 think_chain {seeded:1, steps:1, ms:46}
- **探索 KPI 正信号** (R288/R289): 可达 URL 24 案 A/B — hit **0.278→0.667 (+39pt) ↑7 ↓0 零回归**; wall B≤A (成本不可见); explore_eval 独立跑测程序 + 本地夹具 8 页 + A/B 开关 AGENTFRAMEWORK_EXPLORE
- LinkRegistry 激活链 (R276/R282): 三信号 (锚定/稀缺出链/路径递进) ≥3 激活+父链保护; 真机 link_activation {urls:5, activated:5}
- think-memory 持久化 (R283): Save/Load (STJ source-gen 流式零反射) — 新进程 recall hit top_sim 0.9701 (data/think-memory.json)
- 微步骤宿主链 B2 (R274): gate=IsolatedMicro → 微问询 → 回注 ≤200tok/条; E2E 2860ms failures=0
- 压缩失败防护 D1-D4 (R262-R265): 异常隔离/数字+URL 哨兵 (链接文档 URL 键全档 100%)/降级链/熔断器; 多轮 3 场景 (A=35/B=12/C=22 压缩事件 sentinel 全 0)
- 多轮 driver 场景参数化 (R278): MT_SCENARIO=A/B/C; 10 轮 repl × 压缩遥测 17-35 事件全健康
- 缺陷台账新增: 跑测程序回复区误报 (R273 修: 回复区提取+否定围栏) / build 单项目不刷 host bin 依赖 (R274 教训) / probe stdout 管道满冻结 agenthost

**v0.13.0**
- 渐进式探索: ExplorationConfig (每上下文区/文本/URL/目录最大探索步 + 全局预算 + URL 深度) + ExplorationPlanner (优先级队列; 用户例: 上下文内 URL > 上下文外目录) — 7 单测
- 思考链 T3: ComplexityGate + EvidenceScorer (多源对比, 单源封顶 medium) + ThinkMemory RAG 联想 (相似问题优先历史高置信链接, 引用后 +0.05 置信, 负样本降权, 30 天衰减) + ThinkChainSession — 12 单测
- RAG 数据文件用户指定: CLI `-rag <path>` / 任务内 `/rag` / env 三入口 (真机三态验证)
- Baseline 换血 (用户钦定): L0-L5 分层; XL 大上下文族真机验证 (XL-01 实测 7010 tok, 回复含全部 ground truth; XL-04 10750 tok); ContextBudgetGate (WARN 6000/HARD 9000, 防抖首次跨越放行修复 — python 复现抓 bug) — 6 单测

**v0.13.1**
- 兜底粘性路由: FallbackConfig (config 开关 + cost_quality 性价比序 + 逐个兜底 + 回复校验, MinReplyChars=2 由 Router 测试实证) + Router 逐个兜底链 (fallback_attempt/fallback_verify_fail 打点) + StickyRouteMemory (三门判定: 相似+意图+实体指纹; 最近成功优先 0.01 容差; TTL 72h) — 11 单测

**v0.13.2**
- 格式修复收敛环: IFormatRepairPlugin + JsonRepairPlugin (栈感知括号修复; 用户破损 JSON 实例回放通过) + FormatRepairLoop (①块内检测→②查找→③校验→④本地修复→⑤LLM 循环; max_llm_rounds 可计数; 技能-校验矩阵硬规则) — 13 单测

**v0.13.3**
- 底座能力长期观察 (用户钦定, 入 master-plan §0-2): 压缩 audit (`--compression-audit`, 104 篇多样态 ground-truth × 4 档 × 3 级别)
- A3 关键句保护修复: TakeSentences 评分保留因果/指令句 — SummarySentences 因果/指令保留 0-20% → 单样式 100% / 多样态 99% (keys) / 85% (指令, 无标点样式待修)
- 429 感知调度: 限流跳过同模型重试直切备 (省 ~1000 tok/次重发)
- token-breakdown 每批观测行 (prompt/history/completion)
- 微步骤隔离设计 A6 (阈值门控, 更正2: 未达阈值走常规; 触发率基线 0%)

**缺陷修复 (本段)**: 真缺陷 65 (重试/切备成功路径 llm_call 打点缺失→429 后 token 全丢, 批187 假性 KPI_BREACH) / 66 (文本请求备选落视觉模型成本倒挂) / 67 (Text 能力硬过滤, cogview 误入文本备选) / 68 (C17 断言脆性 → neg_context_markers 推测围栏, 双向回放验证)

### 📊 基线
- 测试: **468/468 全绿** (404 → 468, 含探索 7/思考链 12/兜底粘性 11/格式修复 13/预算门 6/视觉族 3)
- AOT: publish 0 IL 警 (多次重发布); 批测: 批 174-217 带内 (600-1250 tok/case), full-23 23/23
- 文档: CLI 指令说明三表重构 (会话指令/本地命令/启动参数); docs/ 全量审计 (6 文档归档, 断链 0)

---

## v0.12.0 (2026-09-08) — 视觉理解 / 渲染插件 / 收敛环 (已验收)

### ✅ 完成记录 (真实执行)
- **视觉理解链**: CLI `-img` → Message.ImageAttachments → data URL base64 → glm-5.3-flash v4 端点; text-only 模型自动重路由 + coding 端点改写 (真缺陷 63/64); OpenAIMultimodalMessage 双形态 DTO (string|parts[], AOT-safe 手写 converter)
- **图像渲染插件体系** (用户钦定收敛环服务化): IImageRenderPlugin 契约 + SkiaSharpRenderPlugin (默认 PNG, 边缘选项 `-p:DisableSkiaRenderer=true` 停编) + SvgTextRenderPlugin (零依赖兜底) + ImageRenderPluginRegistry (HasRenderer=false → 跳过后续环节); LocalSvgRenderer DSL (rect/circle/line/text, XML 转义, 栈感知)
- **收敛环 E2E**: LLM 生成 DSL → 渲染 → 5.3-flash 视觉校验 → FAIL 重生成 → PASS (真机一轮 PASS: DSL 1039ch → SVG 843ch → 校验 6/6, 6.4s)
- **能力矩阵**: models.yaml 25/25 模型 capabilities 回填; CogViewClient 保留 (生成路径按用户钦定 R210 弃用)
- **验收**: T-V01~04 视觉用例族 full-23 23/23 (含负样本诱饵识破: 模型拒绝"右下角苹果"假预设); 四问真机复证; 基线 docs/archive/reports-archived/v012-acceptance-baseline.md

### 📊 基线
- 测试: 415+ 绿 (视觉 DTO 5 + 渲染器 3 + 插件 4); AOT 0 IL 警

---

## v0.11.0 (2026-09-06) — 统一命令协议 + 三传输 + Skill 脚本执行

### ✅ 已完成 (真实执行)
- **agent.io 统一命令协议**: `AgentCommand` 信封 (@cmd name key=value 行协议, 百分号转义手写编解码 — 零依赖 AOT 安全) + `AgentCommandWriter/Reader`; AgentReportReaderBase 加 Command 事件分类
- **三种传输**: Console.IO / 共享内存 (文件-backed mmap 环形区, 背压可见) / TCP Socket (跨机)
- **LogRouter 双通道**: thinking/输出指令同时镜像 IChatboxSink + @cmd
- **SkillScriptRunner**: SKILL.md 包 scripts/ 真进程调度 (python/bash/node PATH 探测; cwd=包目录沙箱; 环境变量白名单; 超时杀进程树; 脚本 @cmd → AgentCommandWriter 转发)
- **SkillDispatcher 接线**: executive 无显式 entry → 包脚本自动执行
- **性能修复 (sync-over-async 清剿)**: ModelQueueRouter.OnTransientFailure → async 链; TriggerMatcher.MatchAsync; ContextGradientCompressor.CompressCoreAsync
- **模型目录 6 → 18**: +Anthropic/Google/xAI/Moonshot/Qwen/DeepSeek v3.2/OpenAI/GLM-4.5 — 全部公开牌价, /model verify 可校验

### 📊 基线
- 测试: **351/351 全绿** (+10: 命令协议 6 + 脚本执行 4)
- AOT: publish 0 IL 警; /model list 18 模型真机确认

---

## v0.10.0 (2026-09-06) — Yamlify 换库 + Token 统计/余额联动 + Skill 语义

### ✅ 完成记录 (全部真实执行)
1. **YAML 解析换 Yamlify 1.8.0** (MiniYaml 重写为门面): AOT 零 IL 警; `TryGetTopLevel` 修复顶层列表键真 bug; API 签名不变 → 5 消费者零改动
2. **Token 使用统计 + 余额联动** (TokenUsageService): 真实 API 同步 → 本地累计 → 阈值再同步; 余额不足切模 + flags 提示; `/token stats` 全 JSON
3. **Skill P3 语义匹配接 bge** (TriggerMatcher): 词面全未命中 → bge 余弦 ≥0.45 疑似判定; 失败静默回退词面
4. **官方端点可配置代理** + **统一输出收口** (host 8 处 Console → IOutputSink; 库内零 Console 直写) + **/forecast 指令** + **/model list 序号选择** + **LocalLlamaCaller DI 修复** + **版本号统一 15 csproj → 0.10.0**

### 📊 基线
- 测试: **341/341 全绿**; NativeAOT publish 0 IL 警 (agenthost 12MB ELF); AOT 冒烟 4 项通过; GitHub 推送 387bfb1

---

## 历史遗留 (v7.x — v0.x 前身版本号体系)

> 以下为 v0.x 统一编号前的历史记录, 原文保留; 详情见 git log 与 docs/changelogs/CHANGELOG-v7.14.md。

### v7.15 (2026-09-05) — 十节点全落地
十节点: ①Skill 调度 P1 ②模型队列与意图选模 ③日志四通道 ④上下文梯度压缩 ⑤影子计划 ⑥问询打通 ⑦会话恢复 ⑧公开配置读写 ⑨agent.io 协议库 ⑩能力插件接口。需求四项: ①官方通道混合调度 ②agent.io ③会话中断恢复 ④公开配置读写。基线: 276→325 测试全绿 / AOT 0 IL 警 / 双冒烟通过。

### v7.14 (2026-09-05)
EvidenceGate→ClarificationBatch 接入 V2 主链 / vulkan setenv 双写 / SessionMemory 滚动 / AgentProfile 动态学习 / CapabilityScanner 重构 / 目标锚免压缩 / 面板全 JSON。基线 218/218。

### R380 承接: BGE 训练闭环打开后的首个诚实结论 (待核实 1 项)
- **闭环通了**: 模型路径候选回退 + 矩阵形状归一后, `train_adapter.py` 96s 内跑完并把 `docs/reports/bge/versions/v1.md` 写出 (此前 3 次全在 900s 死等后失败)。
- **诚实边界**: 判定 `rolled_back` —— T1 适配器 **未过 G1/G2**(r@1 0.2667 vs 基线 0.3083), 闸门正确拒绝采用劣化模型 (负样本诚实原则生效)。
- **已定位并修复 (R380 收口)**: ridge 配置 r@1=0.0/median_rank=999 的根因是**两层真缺陷叠加** —— ① **拟合空间 ≠ 应用空间**(拟合用未 λ 缩放的 `_base`, 应用时 W 乘在 `_base/λ^α` 上); ② **转置错**: `(QᵀQ+λI)⁻¹QᵀP` 是**列定向**解(= Wᵗ), 旧代码直接 `matvec(W,·)` 当 W 用。
  - 统一出口转置 + 同空间拟合后真机: **median_rank 999 → 23 / r@1 0.0083 → 0.1750 / r@10 0.0583 → 0.4250**。
  - 机检 `eval/bge/test_ridge_space.py` (同空间 cos **1.0000** 精确复原 + 异空间**反向控制**必须显著变差) → 4/4。
  - **结论订正**: ridge 在修正实现下仍不及基线 (0.1750 < 0.3083, G1/G2 未过 → `rolled_back`), 故"ridge 无收益"这回**有依据**; 此前结论建立在错误实现上, 不成立。

### R383 (2026-09-13) — D4b 出站扣减 + T4 真跑闸门决策 + D7 运行时依赖等待
- **D4b 出站扣减** (修 R382 §9.5-2 的重复计算): 已判**本地执行**的子请求**不再发给模型** —— 路由是"谁来做", 不是"记账"。三层确定性判据 (节点级 R2c / 片段级 `RequestAblation` / 计划级闸门"仍有远程节点才扣"), 保守方向"定位失败/多处/剩余<25%/全本地 ⇒ 一律不扣"; 扣减掉的子请求由框架自渲染进答复 (`PlanLocalAnswer`, 失败也如实说明)。**真机**: 远程节点 **2→1**、出站 **117→100 字符**、答复里的字数由模型自算 **118(错)** 改为框架算 **117(对)**、tokens 38,275→30,501 (指示性)。机检 `PlanAblationTests` **24 例**。
- **T4 决策**: `AGENTFRAMEWORK_PY_RUN` **空值 ⇒ 默认跟随"是否已装固定解释器"** (只有 PATH 兜底时保持不跑 —— 不可复现的通过比不通过更危险); 解析顺序单一事实源 (`explicit → 仓库固定记录 → uv 托管 → PATH`), **解释器来源进结果与遥测**; `scripts/fetch-py-tool.sh` 固定 CPython 3.12.14; 闸门只对 `.py` 开放。**真机**: `script_run{ran:true, exit:0, ms:32, interp=…cpython-3.12.14…}`。机检 `PythonInterpreterResolverTests` **9 例**。
- **D7 运行时依赖等待** (用户 OOB 新增测试点): A 跑到中途要用 B 的产出, 而 B 未产出/在等用户 ⇒ **A 等待, B 产出后才继续** (不消费输入/不伪造/不静默)。确定性契约 `$node:<id>`、`$dep:<id>`、`<id>的产出`; **等待不占并发额度** (延迟队列, 额度=1 也不死锁); **有界等待**超限如实失败 (不采用迟到产出); **成环在记账时即拒**; 生产节点在等用户 ⇒ `PausedForDependency`; 提前终止时等待节点明确落终态 (不留悬空 Waiting); 前端可见 `plan.node{state:Waiting, wait_for, wait_reason}` + `plan_wait` + KPI `WaitNodes/WaitUs`。机检 `PlanRuntimeWaitTests` **11 例**。
  - **诚实边界**: **跨轮唤醒 (D7b) 未实现** —— 检查点 `SaveCheckpoint` 只写不读 (无 `LoadCheckpoint`/续跑入口), 用户回复后不会自动续跑; **自然语言引用不认** ⇒ 真实任务要出触发点必须先做契约**前置注入** (D7c)。
- 基线: **949/949** (891 + PlanLocalFirst 14 + PlanAblation 24 + Resolver 9 + RuntimeWait 11); AOT 发布校验按登记口径只在发布 tag 执行。

### R384 (2026-09-13) — D7b 跨轮唤醒（装载入口 + 续跑消费方）
- **补齐结构缺口**（R383 诚实边界 1）: 此前检查点 **只写不读** —— 生产节点在等用户时计划停在 `PausedForDependency`, 用户把答案发回来**没有任何消费方**（被当成全新任务重拆, 永远等不到续跑）。本轮加 `PlanResumeService`：**Capture**(蓝图+运行态+真产出+卡住节点+问题) → **Load**(拆解**之前**拦截, 从检查点重建 plan/run) → **ApplyReply**(答复落到确定参数槽) → `PlanRunner.RunAsync(seedRun)` 从上一轮运行态继续, 已 Completed 节点**不重跑**、等待节点被**真产出**唤醒。
- **四条硬纪律（机检逐条钉）**: ①不重拆（拦截点在意图拆解前）②不伪造（生产者已 Completed 而快照缺其产出 ⇒ 装载入口**直接拒绝**, 不接受空着喂/重跑生产者）③不猜（无参数名/多条目/不在选项内 ⇒ 拒绝落地并作废该检查点, 如实告知）④不留悬空（跑完清检查点; 再次暂停重新捕获; 等待台账跨轮闭合, `WaitUs` 含用户思考时间）。
- **两个实现要点**: `ClarificationsSettled`（答复落地后证据门槛**不再重复问同一句**; 其它低置信节点仍正常提问）; 续跑批次过滤已 Completed 节点（`order` 保持完整以保生产者查找）。
- **跨进程真机证据**（两个独立 dotnet 进程只共享检查点文件）: A(write) `state=PausedForDependency, awaiting=b, order=[]`; B(resume) `state=Finished, order=[b,a], a_input=out-b, slot_value=数据是 42, wait_ms=9`。落盘键位 `PlanJson(1682 字符)/RunJson(625)/NodeOutputs/SourceText/AwaitingNodeId=b/PendingQuestion=要处理哪个文件?`。
- **产品链路真机 E2E**: 用产品序列化器在真机数据目录预置可续跑检查点 → `agenthost --session-id cli-r384probe -q "数据是 42"` → `plan_resume{resumed:true, state:Finished, nodes:2, waits:1, slot:target}`、两个节点全本地 `Completed` (`tokens:0`)、**整轮遥测无 `llm_call`（零 LLM 调用/零 token）**、答复渲染为 `🔄 续跑计划 r384-probe …`、跑完检查点由产品自己清掉。附带产品改动 `--session-id <id>`（原会话 Id 每进程随机 ⇒ 跨进程可复现性不成立）。
- **诚实边界**: D7c 契约前置注入**未做且查明落点不存在** —— 当前**没有逐节点远程生成**（一次远程生成覆盖整段计划, 节点文本由确定性拆解产生, 无"节点级提示词"注入面）; 要落 D7c 须先决策"拆成逐节点生成"还是"把契约塞进同一次生成的指令区"（后者需计划先于出站请求成立, 可进静态前缀缓存）。续跑入口**只认"等用户答复"**（纯等待/崩溃中断不自动续跑; 等审批故意不捕获, 否则会吞审批消息）; 多条目澄清需"逐项答复协议"; 答复落点语义与主链 `AnswerSink`（无槽时挂节点文本）**不一致**; `WaitUs` 跨进程锚点不同 ⇒ 跨进程等待时长只作参考。
- 机检: `PlanResumeTests` **18 例**（6 正向 + 8 负向 + 2 跨进程探针 + 1 审批负向 + 1 产品链路探针）; 基线 **967/967**（949 + 18 新增/探针）。

### R388 (2026-09-13) — 形式化内核三缺口全修 + DCR 口径修正 + z3 独立审计器

- **内核完备性三缺口全修（自检 14/14）**: ① **整数 gcd 必要条件**（显式等式 `Σaᵢxᵢ=b` 且 `gcd(aᵢ)∤b` ⇒ `Sat.Unsat`；必要条件 ⇒ **只可能新增 Unsat，无假 Unsat**）；② 反例搜索窗口由硬编码 `±65536` **参数化**（窗野外可取点、外框无界 ⇒ Unknown）；③ 等式代入由"出现次数最少"**单点启发式**改为**对每个 |系数|=1 的候选主元都代入**（旧启发式挑到 `b` 致目标变量留在策略值上 ⇒ c052–c054 永取不到反例）。修后 c018/c023/c024（传递）、c044/c052–c055（域小）、c066/c074/c077/c079/c081（整数）**全部转决**，13 条不一致 → **0 条**。
- **真装配复跑（L3，零 LLM 调用）**: `agent --formal-eval eval/dcr/dcr_cases.jsonl` ⇒ 145 行 / `gate_enabled=True` / exit 0；**DCR（弃权计合规）= 145/145 = 100.00%** · 保守口径 101/145 = **69.66%** · **可决断集覆盖率 101/101 = 100%** · 决断条目一致率 100% · **主动误判 0**。R387 旧值 91.03% / 60.69%。
- **口径修正（诚实，旧结论作废）**: 原自定"覆盖率 ≥70%"**数学不可达** —— 19 条 `out_of_fragment` + 25 条 `malformed` 共 **44 条设计上就不该决断** ⇒ 上限 101/145 = 69.66% ⇒ 这是**口径设定错误**，不是能力不足 ⇒ 已改**可决断集覆盖率**（分母 = 可决断集）。
- **新增第四条验证腿（独立审计器）**: `eval/dcr/audit_decisions.py` **不 import 内核任何代码**，用 z3 逐条复核装配裁决 —— `Refuted` 反例必须真满足 `premise ∧ ¬goal`、`Proved` 必须真 unsat；实测 **30/30 反例为真 · 33/33 真 unsat · 0 假（`AUDIT_RESULT=SOUND`）**。"反例不是编的、证明不是假的"从此**可机检复现**（换独立实现对账铁律再落一条）。
- **内核层 vs 装配层 19 条差异 = 层职责**（18 条 absent 的 `NoFormal` 语义 + 1 条 goal-only 的契约结构完整性）⇒ **不是判定错误**，装配层才是契约语义的裁决。
- **诚实边界**: **T1–T4（FAVA 的 DCR 公式/分母/弃权处置/aggregate 合并）仍不可得** ⇒ **"达到 90.5%±5pp"仍不能单口径断言**（100% 与 69.66% 分落区间上/下，**达标与否完全取决于弃权是否计合规**）；**【R397 更新】T1–T4 已解(FAVA 正文取证) ⇒ 单一口径定稿 = 145/145 = 100.00%；但口径敏感度实测 30.34pp，且 90.5% 是 801 例 aggregate(含降层损失)、与本仓 145 例不可比 ⇒ 该断言仍不成立；瓶颈已从「口径未知」转为「题集饱和(无区分度)」。**当前题集已**饱和**（100% 无区分度）⇒ 下轮须加硬用例（长轨迹 / 语义降层类）。
- 机检: 全量 **1019/1019**（含 kernel 共享源）；内核自检 `check --selftest` **14/14**；`XCHECK{agree=15, int_gap=0, unsound=0}`。

### R388b (2026-09-13) — agent.rover Transformer 前向推理真机对账（焦点①）

- **交付**: `src/agent.rover/infer/{ModelConfig(152),RopeTable(73),KvCache(100),ForwardPass(303)}.cs` + `Cli/ForwardCli.cs`(173)（新增；未改 csproj、未加 NuGet、零反射、输出走 `TextWriter`）。
- **Phase 1 数学自证（tiny f32，同权重两侧各算）**: GQA(4/2)+untied 与 MHA(4/4)+tied 两个 tiny ⇒ logits `max_abs_diff` **7.27e-06 / 7.63e-06**（判据 <1e-4）· top-5 id **全同** · **逐层逐 token** hidden 对账最差 5.91e-05（相对 ≈1.3e-06，纯 f32 归约次序）。
- **Phase 2 真 7B（DeepSeek-Prover-V2-7B GGUF-Q4_K_M，4.22 GB）**: 单 token **top-1 = 185**、耗时 16.7–19.4 s、**峰值 RSS 374.7 MiB**（numpy 独立参考 **1.98 GiB**，`Swaps: 0` 侥幸通过）；4 token KV cache `kv_len` 1→2→3→4、**top-1 = 13、top-5 = [13,16,17,15,18] 与 numpy 完全一致**、logits `max_abs_diff 6.10e-05`。
- **"没有 7B 张量被全量物化"有账**: `streamed 4023.0 MiB / file 4028 MiB → ratio 0.999`（单 token 把整份权重流式读一遍）、常驻仅 **976 KiB**（61 张 norm）；numpy 参考物化整张 ffn ⇒ 1.98 GiB。
- **主线程独立复核（不采信子代理自报）**: 重跑 tiny + 真 7B 单 token + numpy 参考 ⇒ 逐位复现（`7.27176666e-06`、`top-1=185`、`2.174377744e-04`、top-5 全同）。
- **诚实边界**: 本模型实测**非 GQA**（`n_head_kv = n_head = 32`）、**无 RoPE scaling** ⇒ 两分支只由 tiny 覆盖；**未实现采样/生成循环**（无 temperature/top-p/EOS）；**未做性能优化**（22.2 s/token 受"每 token 重读 15.1 GiB 权重"限制）；单 token logits 绝对差 **2.17e-04 > 1e-4**（值域 44.7–64.5 ⇒ 相对 3.4e-06；top-1 判定裕度为误差的 **645×**，argmax 不在可翻转临界）。

### R389 (2026-09-13) — agent.rover Vulkan 真机落地 + SPIR-V 常量表权威机检（焦点① GPU 路径）

- **旧假设被探针证伪（诚实修正）**: 此前计划书写"本机无 GPU ⇒ Vulkan 只能编译 + 真调 `vkEnumeratePhysicalDevices` 得 0 设备"。`vulkaninfo --summary` 实测 **GPU0 = llvmpipe (LLVM 20.1.2)**（lavapipe 软件 Vulkan ICD 已装）⇒ **Vulkan 路径可真跑 dispatch 并对账**；本轮据此把 GPU 路径从"仅编译"升级为"**真机跑通 + 数值对账**"，并回改 exp10 计划的 C5/GPU/A6 条目（不留旧结论）。
- **交付（全部自研，零 shell / 零反射 / 无 glslang·glslc 环境）**: `Gpu/VulkanBackend.cs`(419 行, instance→物理设备→队列→设备内存→缓冲上传/回读→描述符集→计算管线→dispatch) + `Gpu/Spirv/{Spv.cs(指令级汇编器), Kernels.cs(四内核), SpirvValidator.cs(**独立**结构校验器), SpvDisassembler.cs(**独立**反汇编器, 不入执行路径)}` + `Cli/VulkanCli.cs`(`vulkan` 子命令 / `--spirv-only` / `--spv-dump` / `--show` / `--elements` / `--repeat` / 5 组 `NegativeControl`)。运行库 = `Silk.NET.Vulkan 2.23.0`（与 Silk.NET 同源, 非自造 P/Invoke; API 形状先由一次性反射探针 `/tmp/vkprobe` 定死再写静态代码, 探针不入产品）。
- **真机结果（全绿）**: 三内核数值对账 `fma_vec max_abs_diff=0` / `silu_mul 2.98e-08 < 1e-5` / `scale_inplace max_abs_diff=0`；机制探针 `const_b1_hits=4/4`、`dyn_b2_hits=16/16`、`dync_b3_hits=16/16`、`index_value=8 ∈[0,16)`；`done{kernels=3 pass=3 fail=0 spirv_valid=3 neg=5/5}`；build **0 Warning / 0 Error**。
- **共修 4 处真 bug（前 3 处由独立件抓出, 第 4 处只能由外部权威抓出）**: ① 汇编器 `ExecMode` 丢 mode 字面量 ⇒ 非法 SPIR-V；② 结构校验器 bound 读错 word（`words[4]`→`words[3]`）；③ `AccessChain` 缺 struct 成员索引 0（结构合法、语义错）；④ **自写 opcode 常量表两处错值** —— `OpUGreaterThanEqual = 179`（规范 **174**, 179 实为 `OpSLessThanEqual`）、`OpConvertUToF = 111`（规范 **112**, 111 实为 `OpConvertSToF`）⇒ 守卫 `I >= n → return` 编译成了带符号/浮点比较 ⇒ 条件失效 ⇒ 全部 256 个调用都跑 body ⇒ 动态索引写落 0..255 越界不可见（表现为"dispatch 成功但动态索引写不落地"）。
- **本条最重要的方法论升级（与既有「跨实现交叉对账」铁律同源, 但更狠）**: ④ 号 bug **汇编器、结构校验器、反汇编器共用同一张手写常量表** ⇒ 三者会**互相印证同一个错误**（校验器报 valid、反汇编"逐字正确"）—— 自证链**在原理上看不见**它。只有引入**外部权威 oracle** 才抓到: Khronos 官方 `spirv.core.grammar.json` + `extinst.glsl.std.450.grammar.json`（已钉进 `Gpu/Spirv/registry/`, 附来源 URL + sha256）。**封死措施**: 新增 `SpvRegistryAudit.cs`（零反射 JsonDocument 审计器）+ 机检 `SpvRegistryAuditTests` ⇒ **100 条常量 / 0 不符 / 0 无法核对**, 且带 **4 组负向控制**（改错 opcode / 改错枚举 / 改错 GLSL.std.450 号 / 注入表外常量各一例必须红）—— 审计器自身"没测到"一律进 `Unverified` 而非静默放过（"未验证 ≠ 已验证"）。
- **诊断纪律（可复用）**: "dispatch 成功 ≠ 数值正确" ⇒ 先加数值转储, 再把失效点**逐机制二分**（ArrayLength / 常量索引 / 动态索引 / 常量值+动态索引 / 缓冲绑定位置）；"结构合法但数值错"必须用**独立反汇编器取真值**（据此**证伪**"'SPIR-V 层绑定/装饰错位'整类猜测", 真问题是诊断夹具自身缓冲顺序错位）；夹具缓冲序必须与内核变量声明序**逐位对齐**, 否则错位会伪装成"设备写未落地"。
- **诚实边界**: GPU0 是 **lavapipe 软件实现**, `device_ms`/`elem_per_ms` 只作正确性证据、**不代表真实 GPU 性能**；**CUDA 路径未实现**（本机无 NVIDIA 设备）；Silk.NET 的 Vulkan API 形状由一次性反射探针确定（探针在 `/tmp`, 未入产品）；`/usr/share/vulkan/explicit_layer.d/` 无 validation layer ⇒ 结构校验靠自研校验器 + 5 组负控背书（非 khronos 官方校验层背书）。
- 机检: `SpvRegistryAuditTests` **6/6**（含 4 组负向控制）；全量测试 `1025/1025`（1019 + 6 新增）；`vulkan` 子命令 exit 0。

### R390 (2026-09-13) — agent.rover 驻留/回收接前向：热集常驻 + LRU 主动驱逐真触发（焦点① 剩余件）

- **本条要修的靶点（用户口径 C3/C4 的空白面）**: 此前驻留账**恒 `evicts=0`** —— 即"只常驻活性高的张量 + 不再使用的张量主动从内存释放"里的**驱逐/回收路径从未被走到**，且 `TensorResidency` **未接进前向**（前向完全不走驻留管理）。
- **交付**: `Infer/ForwardPass.cs`（cts 增 `pins` / `reclaimPerToken` 两参；每 token 末 `ReclaimAll()`；暴露 `ResidentCount`）+ `Cli/ForwardCli.cs`（`--budget-mb|--budget-kb|--budget-bytes` / `--no-pin` / `--reclaim-per-token` + `residency_scope` / `residency_verdict` 两行账面）+ 新件 `Cli/ResidencySelfTest.cs`（**10 例自证套件**，真张量夹具，零 shell 零外部进程）+ `Runtime/TensorResidency.cs`（预算语义显式声明 `Ledger.BudgetUnlimited`）。
- **真机证据 · 接前向对账（判据：受限 vs 默认逐位一致）**:
  - tiny（`tiny-gqa-untied.gguf`，3 token）：`--no-pin --budget-bytes 256 --reclaim-per-token` ⇒ `evicts=9 reclaims=12 loads=13 peak_resident=512 budget=256`，`peak = 预算 + 单张量字节`（驱逐确实发生了才可能压到这个值）；**8/8 dump 文件 `cmp` 逐位一致**（logits sha256 `c5bbb3f546a640be`）。
  - 真 7B（4.22 GB）：`--no-pin --budget-bytes 16384` ⇒ **`evicts=118 reclaims=120 loads=121 peak_resident=32768`**；**top-1 = 185 与默认一致**、`logits.bin` sha256 `e34dabd647b50ba0` **逐位相同** ⇒ 驱逐/重载**不改变数值结果**（重物化走同一确定性反量化路径）。
  - 热集常驻（默认 pin 全部 norm）：真 7B `loads=61 hits=60`（第 2 token 起 60/61 命中）、常驻 **999,424 B ≈ 0.023%** 模型体积。
- **自证套件 10/10（真 7B + tiny 双夹具，`residency --selftest <gguf>`，exit 0）**: 预算约束上界 / LRU 驱逐真发生 / **LRU 受害者次序** / **真释放判别** / 账本恒等式 `loaded == resident + reclaimed` / pin 免疫 / 流窗口零物化（量化权重驻留恒 0）/ `ReclaimAll` 释放额精确 / **负控①**全 pin + 预算 1B ⇒ 必须 `evicts=0` 且如实报 `budget_exceeded_honest` / **负控②** 预算语义只声明一次。
- **本轮修掉的两处真缺陷（均为"两层口径不一致"，非表面 bug）**: ① `EnforceBudget` 首行 `if (Ledger.BudgetBytes <= 0) return;`（0 = 无上限）与 CLI 判语 `peak <= budgetBytes`（0 预算 = 必然超限）**各自解释同一个数字** ⇒ `--budget-mb 0` 时账面同时出现"无上限未驱逐"与 `budget_exceeded_honest`。修法：语义**只声明一次**（`Ledger.BudgetUnlimited = budget <= 0`），判定与打印**同源派生**，并补 `--budget-bytes` 表达真子张量级预算（0/负 不再是唯一能表达"很小"的手段）。② **自证断言本身写错**：LRU 次序原在 12 次取用**之后**判定，而 `small[1]` 早已被后续驱逐 ⇒ 断言误红；改为**在驱逐发生的那一刻**判定（事后观测会被后续驱逐掩盖）—— 记入"机检须在事件时刻判定"的可复用教训。
- **诚实边界**: ① 本机 2 vCPU / ~2.2 GiB 可用内存 ⇒ 预算强度只覆盖"小到能触发驱逐"的量级，**未做长序列下的峰值 RSS 压测**；② 驱逐策略是 **LRU-on-tick**，热集晋升（`IsHot` 访问计数）**在前向里未作为驱逐豁免使用**（前向只在 `--no-pin`/默认 pin 两档间切换，未实装"访问计数晋升为常驻"）；③ `--reclaim-per-token` 后每 token 重物化 norm（`hits` 归 0），是**故意**的对照档，不是默认行为；④ 未做多线程/流水线下的驻留并发安全论证（前向当前单线程）。
- 机检: `residency --selftest` **10/10**（真 7B + tiny 双夹具）；Vulkan/内核回归未受影响；全量测试 **1025/1025**。
- **机检有判别力的当场实证（诚实记录）**: 本轮登记表条目**第一次写错**（把 `evidence_path` 写成"源文件 | 报告"两段式）⇒ `VerificationFormTests.Registry_Exists_And_HasNoViolations` **当场判红**（`evidence_path 不存在`）⇒ 改回单一存在路径 + 新增独立 `evidence_report` 字段复跑全绿。自查不是空断言，本轮由它挡下一次。
- **证据报告（真机输出逐字，45 行）**: `docs/reports/r385/residency-evidence.md`（自证 10 例明细 + tiny/7B 对账 + `cmp` 逐位结果 + 复现命令）。

### R399 (2026-09-13) — 题集加硬(M6) + 跑测数据打点(KPI) + 本机 agent.rover 引擎读数

- **靶点（用户令"用你的推荐方案…不用问询我 + 给 KPI 打点 + 我可以看到具体提升报告"）**: R398 的诚实边界写明"6 题 100% ⇒ 对能力提升零区分度"，且**作弊解仍拿 22.2% 用例级通过率** ⇒ 加硬必须作用在隐藏用例的对抗性上；同时"提升"必须可量化 ⇒ 需把每次真机运行的通过率/耗时/token/失败模式落成台账与前后对比报告。
- **交付**: `eval/probe/tasks.py`(627→853，对抗用例机制 `HARD_INPUTS` + 新陷阱族 `pair_closest_abs_sum` + 见证型数学族)、`eval/probe/grade.py`(300→406，`_verify_witness` 独立验证见证 + `wrong_witness` 失败模式)、`eval/probe/run_probe.py`(380→440，族池接线 + `--families`/`--dump-tasks` + 题集 sha 单口径)、新件 `scripts/kpi_probe.py`(418，台账+对比报告+24 条负控)、`eval/probe/README.md`、`docs/plans/v0.25.0-r399-probe-hardening-and-kpi.md`。
- **加硬三层（可复核）**: ① 每程序族钉死 3–5 条边界输入（全负/单元素/10^9/并列/满字母表…）**只进隐藏集**，不足 3 条即**拒发题**；② 新陷阱族 = "两数之和绝对值最小"（朴素写法在同下标复用/并列取值上翻车）；③ 见证型数学题（`x²≡a mod p`、最小反例）⇒ 判定改为**独立验证见证语义**（最小反例还要复核 `∀m<n` 成立），不比对任何标签。
- **真机读数（同题集 sha 内可比）**: agent 全量批 35/35 用例 = 1.0000、整题 6/6、**56.09s**、8 次 LLM 调用、prompt 21,530 / completion 4,845 / **4,396 tok/题**；定向批（新族）36/36、整题 6/6、215.01s、**11,215 tok/题**；**作弊解 22.2%→6.25% 用例级、整题全对恒 0/3**；`oracle` 0.71s 满分（管线正控）。**结论: 加硬只加硬了"对作弊解的判别力"，对 agent 仍饱和 ⇒ 下轮换维度（多步需落盘/缺信息反问/证明链）**。
- **本轮 6 处真缺陷（含 2 处"口径假设错 ⇒ 空心指标"）**: ① 见证型族**从未被抽到**（题池只取 `MATH_FAMILIES` ⇒ 新功能不可达）② 题集 sha **双口径**（生成 vs `--tasks` 复用）③ KPI 时间窗锚点写反（`ts` 是**结束**时刻，写成 `[ts, ts+elapsed]`）④ 遥测 7 位小数时间戳解析失败被 `except: continue` **静默跳过**（token 全 None 且不报错）⑤ `grade_program` 无 `since` ⇒ 产物新鲜度负控从未跑到（假绿）⑥ **R398 漏下的登记表回归**: `evidence_path` 写成 `';'` 多路径 ⇒ `VerificationFormTests` 判红（全量回归当年跑在登记表改写**之前**）。
- **立规（可复用教训）**: KPI/判定的**口径假设错不会报错，只会把指标变成 None/0** ⇒ 每个窗口/口径都必须配一条"锚点写反必须读不到"的反向负控；任何**证据/登记表改写之后必须立刻跑形式校验**（不能只跑功能回归）。
- 机检: 生成器 **39/39**、判定器 **25/25**、编排器 **18/18**、KPI 打点器 **24/24**、`VerificationFormTests` **6/6**。
- **诚实边界**: ① agent 侧仍 100% ⇒ 题集对能力提升仍无区分度；② 数学题仍只判终值/见证，**不判推理链**；③ 沙箱**不是安全边界**（隔离目录+超时+`-I -B`，**不禁网**）；④ 本机唯一 Vulkan 设备是 llvmpipe 软件 ICD ⇒ 引擎读数**只代表 CPU 路径**；⑤ **agent.rover 目前不是解法后端**（只有 `forward` token→logits，缺 tokenizer/采样/解码环）⇒ 已列为 R400 首要工程项。
- **证据报告**: `docs/reports/r399/r399-m6-hardening-and-kpi-datapoints.md` + 机器生成的 `docs/reports/r399/kpi-probe-r399.md`。

### R400 (2026-09-14) — rover 生成链：分词器 / chat template / 采样 / 解码环（本机引擎可当解法后端的前提）

- **靶点（用户令「继续下轮」+「**注意 rover 也在该一直执行任务规划内**」）**: R399 诚实边界写明「agent.rover 目前**不是解法后端**（只有 `forward` token→logits，缺 tokenizer/采样/解码环）」⇒ 本轮补齐**生成链**，且全程落在任务规划体系内（计划文档 + TaskPlan 节点 `dev-rover-gen` + 长期看板 L8 + 登记表行 + 主报告 §7）。
- **交付**: 新件 `src/agent.rover/token/{ByteUnicode,Pretokenizer,BpeTokenizer,ChatTemplate,TableSnapshot,TokenizerAssets.g.cs}`、`src/agent.rover/infer/Sampler.cs`、`src/agent.rover/cli/GenerateCli.cs`（`tokenize`/`generate` 子命令）、`src/agent/agent.csproj`（共享源编译，纯 BCL）；资产入仓 `eval/rover/tokref/`（表快照 + 5 组夹具 + manifest）；生成器 `scripts/rover_{gen_tokenizer_assets,probe_oracle_predicates,build_tokenizer_fixtures}.py`；测试 `src/agent.tests/Rover{Tokenizer,Sampler}Tests.cs`（22 条）。
- **对账口径（跨实现铁律）**: oracle = HF `tokenizers` 0.23.2（**独立实现**）；**199 encode + 199 预分词 + 2000 压力 + 405 解码**夹具逐条相等；chat 渲染 12/12 与 jinja2（transformers 同引擎同参数）逐字节相等；GGUF 装载路径与表快照路径**同摘要**（`merges_sha256=cb5bed793622288a…`、`tokens_sha256=6e5117ddc01e0cb3…`）⇒ 脱离 4.2 GB 模型可复跑全部对账。
- **本轮 5 处实测修正（都是「看起来对」的失效形态）**:
  ① **.NET Regex 不可用于增补平面字符类** —— 它按 UTF-16 码元解析，`𐐀-𐑏` 被拆成孤立代理项 + 反向区间 ⇒ 静默过量匹配；改为生成器把正则机器解析成**标量区间表**，C# 侧标量扫描。
  ② **区间表必须归一化（排序+合并）** —— CJK 正则原文顺序 `一-龥` `ࠀ-一` `가-퟿` 非升序，首版透传致二分查找漏判（`中अआ文` 被切成 3 片）⇒ 归一化 + 新增自检项「严格升序互不重叠」。
  ③ **`\s?[类]+` 的空白前缀需要回溯** —— 贪婪吞空白后若其后不是类字符，必须退回「不吞空白」，让该空白字符本身作为类成员被匹配（U+3000 同时在空白集与标点/CJK 类内）。
  ④ **判定谓词必须逐阶段隔离探测** —— 用整条流水线探测 `\s` 会被后续 CJK 阶段二次切分干扰（把 Zs 类空白误判为「非 `\s`」）；正确读数：`\s` = 25 码点 = **Unicode White_Space 全集**（全 BMP 穷举），Digits = `{Nd,Nl,No}`（1831/1831，负控 3920 例 **0 违规**）。
  ⑤ **切分集 = `added_tokens` 全体 18 个**（实测与 `special=true` 无关）；`special=true` 的 3 个只影响 `decode(skip_special_tokens=true)` —— 编码切分集与解码跳过集必须**分别入表**。
- **负控常态化（带判别力读数）**: merges 乱序 **41.5%** / 逆序 **56.9%** / 清空 **95.3%**（依赖合并样本 1814），阈值取 30/40/90%；空切分集必红；朴素整片预分词判别 **137/199**。统计只在**依赖合并表**的样本上做 —— 整片命中词表的文本与合并表无关，计入会稀释判别力。
- **负控当场抓到的真 bug**: `Sampler.NextU64` 首版把状态拷进局部再 `ref` ⇒ 随机源**永不前进**（采样退化为恒定输出），由「平坦分布 300 抽取必须出现 >5 个不同 id」的反向控制捕获并修复。
- **真机读数**: GGUF 装载路径 199/199 + 199/199 + 2000/2000 + 405/405（`pass=true`）；`generate --chat` 7B 真跑（逐 token 墙钟 / `tok/s` / 峰值 RSS / 流式字节数，见 `docs/reports/r400/rover-generation-chain.md`）；探针 `solver=rover` 已接线（远端 API 与 rover 同题同判定器，读数标注 `budget_limited`）。
- **诚实边界**: ① 本机 2 vCPU / 无 GPU / 每 token 流式扫 ≈4.0 GiB ⇒ 生成**不可交互**（≈20–33 s/token），本轮交付「链路正确 + 可对账」，性能线属 R401/R402；② chat template 仅支持 `system/user/assistant` 子集，工具调用与 Jinja 全量属 R403；③ 采样器**不含**重复/存在/频率惩罚；④ 探针 `solver=rover` 为**限量 token 口径**（默认 8），不得读作「rover 能力为零」。
- **机检**: 新增 22 条测试全绿；形式校验（`VerificationFormTests` / `DevPlanDocRefTests`）+ 全量回归见本轮报告。

### R403 (2026-09-14) — RoPE 配对约定按 arch 选择：prover7b 长期带病运行的根因（静默错误）

- **发现路径**: 追查 `qwen2.5-math-1.5B-Instruct` 端到端「能跑但乱码」时做排除法 —— 分词（HF `tokenizers` 独立 oracle，6 串逐 id 相同）、量化类型（逐张量直方图，全在支持集）、配置读取（HF `config.json` 的 `rope_theta=10000.0` 与 GGUF 一致，此前误记 1e6）全部洗清；对照臂 prover7b 同提示输出 ` 6, ` ⇒ 通用机制正常。遂审 RoPE 约定。
- **根因**: 引擎只实现了一种 RoPE 配对（`x[i], x[i+n_rot/2]` 半偏移），而**权威源 llama.cpp `llama_model_rope_type()`**（`src/llama-model.cpp:2584`，vendored llama.cpp 源码）规定：`LLM_ARCH_LLAMA`（prover7b 的 arch）⇒ **NORM**（`x[2j], x[2j+1]` 相邻配对），`LLM_ARCH_QWEN2` ⇒ NEOX（半偏移）。⇒ **arch=llama 的模型一直在用错配对**，位置信息错乱且不抛错。
- **影响面**: R400 那句 `gen_text= 2 2 2 2` **不是模型行为，是本缺陷的症状**；prover7b 全部历史输出在新配对下不可信，需重测。
- **交付**: `infer/RopePairing.cs`（枚举 + 由 `llama-arch.cpp` **机械提取**的 41 个 NORM arch 名单 + `FromArch()`，未收录⇒NEOX 与上游 default 一致）、`RopeTable`/`CpuKernels.Rope` 双实现支持两约定、`ModelConfig` 增加 `required RopePairing`、`ForwardCli.rope_check` 增加**约定负控行**；权威判定表存档 `eval/rover/oracle/rope-types.json`。
- **验证（同命令同参数）**: prover7b logits `stdev 2.376802840591207 → 2.48841954302631`（生效）；qwen2 **全部数字逐位不变**（范围隔离）；负控 `rope_pairing_negctl{active=NORM other=NEOX max_abs_diff=3.7959385 verdict=distinct}`；`RoverRopeTests` **7/7**（两种约定金标向量 + 跨实现一致 + 负控 + 频率表不变性 + **实现↔存档逐项机检**）。
- **通用教训（已落 skill）**: 两个自研实现可能**共享同一个约定误解** ⇒ 交叉验证长期绿灯而实际违规。`skills/independent-verification-before-claim` v1.1.0 新增判据 11「约定负控」：约定取值换成另一种合法值结果必须变；约定必须锚定**外部权威**并提取成存档 + 机检。
- **附带产出**: `scripts/gguf_probe_remote.py` 远程 GGUF 兼容性预探（HTTP range 取头部 ~24 MB，判 arch/特性/量化可实现性，先探再下）。实测：`DeepSeek-R1-Distill-Qwen-1.5B` RUNNABLE；`Llama-3.2-1B` RUNNABLE；`Qwen2.5-0.5B`/`SmolLM2-360M` 含 **Q5_0** ⇒ BLOCKED（引擎缺内核）；`Qwen3-0.6B` 含 **56 个 qk_norm** ⇒ BLOCKED。
- **诚实边界**: ① **qwen2 乱码仍未定性**（分词与 RoPE 均已排除 ⇒ 剩 tied 词表 / attn 偏置 / GQA 三条 7B 未覆盖路径；判别实验 `DeepSeek-R1-Distill-Qwen-1.5B`（qwen2 且 untied）已排队）；② 本轮仅重测「平凡续写」，prover7b 解法级重测未做；③ NORM/NEOX 表来自 vendored 上游快照，上游变更需重新提取。
- **报告**: `docs/reports/r403/rope-pairing.md`。

### R417 (2026-09-14) — 探针反饱和：质量「分数」缺失的机制根因是**题集饱和**（天花板效应）

- **发现路径**: 用户问「当前链产出质量不高，需要回流的是你自己的上下文」⇒ 想做「质量→分数」的闭环，先清点探针读数 ⇒ 发现 `probe-agent-seed20260913.json` 与 `probe-m6-agent.json` 的 **agent 与 oracle 同为整题全对 100%**，同题复跑逐族一致 ⇒ 题集对当前链已到天花板，**任何质量分数都恒为满分**。
- **根因（与仪器坏掉的区分）**: 负控 `mutation:hardcode` 仍为整题全对 0 ⇒ 判定器判别力在，是**被测对象到顶**，不是仪器损坏（不区分这两者会误修错地方）。
- **交付**: `eval/probe/tasks.py` 新增 3 族（程序族 7→10）：`topo_min`（字典序最小拓扑序，有环⇒`-1`）、`vm_run`（微型栈机：跳转/栈下溢/地址越界/10000 步上限 ⇒ `ERR`）、`json_mini`（严格 JSON 规范化：仅 6 种转义、uXXXX 解码且码点 ≥0x20、键按码点升序、重复键后者覆盖、输出无空白、非法输入 ⇒ `ERR`）；每族 `ref`/`check` **两条独立实现**双路径验算（1422 例分歧 0）；`HARD_INPUTS` 增 24 条对抗用例；`gen_program_task()` 支持 `tight_gen` ⇒ **每题强制注入 1 条「合 JSON 但不合本规格」隐藏用例**（浮点/NaN/低码点 uXXXX/裸 TAB）；`run_probe.py` 增族专属缺陷注入 `topo_dfs`/`vm_noerr`/`json_loose`；`scripts/dev_return_digest.py` 增 digest §3「探针分数」（整题全对率 + 用例级率 + 失败模式 + **饱和标记**）。
- **读数（正负控成对）**: 正控 oracle `topo_min`+`vm_run` 49/49（4/4 整题全对）、`json_mini` 36/36（2/2）；负控 `topo_dfs` 24/52 整题全对 **0/4**、`vm_noerr` 29/48 **0/4**、`json_loose` 54/72=**0.75 用例级但整题全对 0/4**（这条正是「打分单元必须是整题全对」的反例实证）。
- **真机（AOT `agenthost`）**: agent 在 `topo_min`+`vm_run` 上 **74/74、6/6 整题全对 ⇒ 仍饱和**（单调性论证：旧判定器只会低估 ⇒ 满分读数在修正口径下必然仍满分）。
- **首个非饱和质量分数（`json_mini`，n=3 真机）**: 记录口径 27/54=0.5 用例级、整题全对 0/3；**修正口径 47/54=0.8704、整题全对 1/3**（p001 12/18 漏引号 · p002 18/18 满分 · p003 17/18，唯一失分 = `tight_gen` 强制的裸 TAB 紧用例）。**用例级 87% vs 整题全对 33% 的落差 = 「判分单元必须是整题全对」的实证。**
- **仪器两处真缺陷（真机暴露，已修 + 4 条负控入 selftest 29/29）**: ① 提取器"首个可编译前缀"⇒ 长回复下 10 KB 程序被判成 46 字符注释残片；② `grade_program` 先看退出码 ⇒ stdout 正确但 `sys.exit(1)` 被判 runtime_error。修复 ⇒ `eval/probe/grade.py` 提取分两轮 + 前缀下限 64 字符、分类改 stdout 优先（`exit_nonzero_ok`）。
- **证据卫生缺陷（本轮暴露，下轮修）**: `data/probe/replies/` 无臂命名空间 ⇒ 后一臂覆盖前一臂（topo/vm 臂 p001–p003 已被覆盖）。
- **诚实结论**: 「加难族」这条路本轮**未打破天花板**（链在程序题上比预期强）；质量从「计数」变成「连续分数」仍需**换维度**（每题 tokens / 轮数 / 首次通过率——对饱和题集仍有区分度，且直接对齐用户 KPI 口径）。
- **计划**: `docs/plans/v0.38.0-r417-probe-anti-saturation.md`；证据 `eval/rover/r417/`；登记 `docs/verification-registry.json` `r417.probe-anti-saturation`（L4）。
- **文档缺口（如实登记）**: `docs/improvements.md` 的 **R404–R416 轮节未回填**；`docs/plans/v715_dev_plan.taskplan.json` 只登记到 R412（R413–R417 未登记）。

### R418 (2026-09-14) — 探针「过程/成本」维度 KPI：成本读数的根因是**归属缺失**，不是缺字段

- **发现路径**: 承接 R417 结论「质量维度被天花板压住 ⇒ 换维度（每题 tokens / 轮数 / 首次通过率）」⇒ 写提取器后**先在旧归档上试跑**，三份不同 run 读出**完全相同的成本数**。
- **根因**: ① `eval/probe/run_probe.py` 回复名 `%s%s-%s`（`--tag` 默认 `""`）⇒ 同一 solver 的不同臂**写同一路径**（R417 已暴露「覆盖」）；② 无命名空间的旧批次**无法确定性归属** ⇒ 若直接取第一个候选，会给出**看似合理的错数**（比缺读数更坏，因为它会被当成证据）。这与 R407 的「自算错而自洽」同族：**错在归属层，不在解析层**。
- **交付**: 新 `eval/probe/process_metrics.py`（349 行）：质量取**判定器产物**、成本取**归档回复原文**；归属三级 = `reply_ns` 精确名 → **时间窗**（`ts - elapsed_s - 5s … ts + 60s`，取自 probe JSON 的 `ts`/`elapsed_s`）→ 否则 n/a；**窗内多候选判歧义、绝不取第一个**；**n/a 不记 0**、均值剔除 n/a；首次通过率只数 `ok ∧ turn==1`，turn 未知的满分题单列 `first_try_unknown`（保守）。`run_probe.py` 归档名带 seed 命名空间（`agents20260916-p001.txt`）+ 摘要记 `reply_ns`。digest §3 增成本列，**质量与成本拼成同一行**（tokens/题、tokens/满分题、turn≤、墙钟均、过程 n/a）。
- **读数（真机 AOT，`json_mini` n=3 seed=20260916）**: 整题全对 **2/3 = 0.6667**、用例级 **52/53 = 0.9811**、**tokens/题 = 9151.0**（prompt 侧）、tokens/满分题 9189.0、墙钟均 **77.7 s/题**、**turn≤1**（零多轮/零追问）、n/a 0、畸形 0。**成对负控**（`mutation:json_loose` n=4，同 seed）整题全对 **0/4**、用例级 0.7324 ⇒ 判别力仍在；该臂不走 LLM ⇒ 成本记 **4×n/a**（记 0 会伪造「零成本」）。
- **诚实边界**: ① 链不落 `completionTokens` ⇒ 只有 **prompt 侧 + 墙钟**；② 探针为单轮 ⇒ 「轮数」目前主要作**异常检测**，首次通过率与整题全对率同分母（真正区分要等链路出现重试/追问）；③ 旧批次（R413–R417，无命名空间）成本**一律 n/a，不做回填**（回填 = 伪造归属）；④ n=3 小样本，非分布。
- **仪器**: `process_metrics --selftest` **14/14**（含反张冠李戴负控、n/a 分母负控、歧义负控）；判定器 29/29；run_probe 18/18；tasks 45/45；kpi_probe 24/24。TaskPlan 已登记到 R418（**21 节点**，末条 `dev-probe-process-kpi`）。
- **计划**: `docs/plans/v0.39.0-r418-process-kpi.md`；证据 `eval/rover/r418/`；登记 `docs/verification-registry.json` `r418.probe-process-kpi`（L4）。

### R419 (2026-09-14) — 探针多轮化：轮数/首次通过率/修复率从「恒等判据」变「可分化」

- **目标**: 让「轮数 / 首次通过率 / 修复率」产生**真分化**（此前单轮 ⇒ 轮数恒 1、首次通过率 ≡ 整题全对率，无区分度）。
- **落地**: `--turns>1` 用**同 sid 跨进程**续上下文（决定性微实验: turn1「记住 4271」→ turn2 命中）；口径铁律 = 轮数取**发送次数 / 归档文件数**（转录里的 `turn N` 是**进程内**轮次，两个进程都写 turn 1）；修正轮默认 **`onfail`**（只对首轮未过题发 ⇒ 前提为真）。
- **三个真缺陷（每个都成对配闸）**: ① 判定器 `run_code` 严格按 UTF-8 解码被测程序输出 ⇒ 程序打印一个坏字节（`0xe9`）即整臂 `UnicodeDecodeError` 崩掉（实测 `STEP_EXIT_agent=1`）⇒ 改字节捕获 + `errors="replace"` + `bad_encoding` 计数（grade selftest 29→31）；② **同 NS 重跑静默覆盖既有读数**（★ 一次真分化读数因此只剩会话记录）⇒ `REFUSE_NS_COLLISION` 闸；③ 首轮失败在日志里不可见 + `reply_chars` 恒 0（归档 11.9 KB 而摘要写 0）⇒ 首轮行原样打印 + 集中回填（run_probe 25→26）。
- **对照臂（假前提）**: `correction=always` 对已达标题谎称「隐藏用例没过」⇒ 首轮 0.6667 → 两轮 **0.0**、回归 **2 题**。教训: **修正轮的前提必须为真**，否则量到的不是「修复率」而是「抗误导性」。产物归档 `eval/rover/r419/evidence-always-correction/`。
- **真机读数（AOT agenthost，`json_mini` n=6 seed=419/420，turns=2 onfail）**: 4 次跑中 **3 次首轮即全对（饱和 ⇒ 判 EXIT 2，不放行）**、**1 次 first=0.8333(5/6) → 两轮 1.0、fix=1.0、回归 0、轮数 7/7 ≠ 6 ⇒ 真分化**（该次产物被同 NS 重跑覆盖 ⇒ 仅会话记录，见 `eval/rover/r419/README-evidence.md`「归档事故」）。
- **控制臂（判别力）**: `mutation:delayfix` **fix=1.0** / `mutation:nofix` **fix=0.0**（三批 n=3/6/6 全成立）；轮数**实到 == 期望**（3/3、6/6、12/12）；检查器 7 态自证（正常0/饱和2/混批3/负控误读2/缺字段3/回归2/NS不符3）。
- **仪器**: run_probe **26/26** · grade **31/31** · process_metrics **22/22** · 检查器自证 **7/7** · tasks 45/45。
- **诚实边界**: 真机侧**未稳定复现**分化 ⇒ 「仪器可用 + 存在分化」**不等于**「r1 链增益已确证」；n=6 单族非分布；`json_mini` 对该链近天花板（R417 的 1/3 读数系**旧提取器**退化所致，提取器修好后分数上移）。
- **计划**: `docs/plans/v0.40.0-r419-probe-multiturn.md`；证据 `eval/rover/r419/README-evidence.md`；登记 `docs/verification-registry.json` → `r419.probe-multiturn`（L4）；TaskPlan **22 节点**（末条 `dev-probe-multiturn`）。

### R420 (2026-09-14) — 「API 落地 ≠ 已接线」：`/recall` 生产消费点（回填：本轮产物已 commit，轮节补记）

- **目标**: `SessionHistorySearch`（R370 交付）在生产里**消费点为 0** —— 能力存在但无人调用，属于「交付完成」的假象。接到本地指令出口 `/recall`。
- **交付**: `src/agent/registry/LocalCommandResult.cs`（`KnownCommands += /recall` + `TryRoute` 臂，四表同步）；`src/agent/IndustrialAgentV2.cs` 宿主 dispatch 特判渲染 + `recall_query` 通道级打点；`SessionHistorySearch.Render`（空命中显式文案，失败可见不静默）；测试 +`CommandRouteConsistencyTests` `/recall` 行 + `SessionHistorySearchTests` 3 条渲染断言（28/28）。
- **真机两臂（L4）**: 治疗臂 `recall_query` 3 事件 / `llm_call` **0**；负控臂（**接线前** AOT 产物）同形输入 `recall_query` **0** / `llm_call` 1 且 stdout **无**渲染 ⇒ 「接线生效且本地指令零 LLM」。C4∧C5 合取才算成立（只有 C4 时，CLI 恒定打印的「意图分析/管线执行」进度行会让人误以为走了 LLM 主链）。
- **诚实边界**: 负控是「接线前 AOT 产物」级而非源码回滚；真机查询 3+4 条非分布；**`hits=0/2` 的质量读数暴露词面重叠缺陷（`不存在`→2 命中）**，登记为下轮候选（→ R421）。
- **计划/证据/登记**: `docs/plans/v0.41.0-r420-recall-wiring.md`；`eval/capability/r420/README-evidence.md`（L4）。

### R421 (2026-09-14) — 跨会话检索的**否定极性**：`/recall 不存在` 不再召回到只断言「存在」的文档

- **发现路径**: R420 的真机**质量**读数（`/recall 外星词根zzq不存在` → 2 命中）不是「没接通」，而是「接通了但答反了」——命中文档全部在断言**肯定**命题（`若图中存在拓扑序…`）。先复现再改码。
- **根因（词元层）**: `Tokenize` 把 `不存在` 切成 `不存`+`存在`，与库里的 `存在` **同词元**；打分为 `score = Σ Idf(t)/√|qSet|`，对否定**无感** ⇒ 否定被丢掉。用受控读数逐位验证公式（n=3、`df(存在)=3` ⇒ `0.5596`；`0.5596/√2=0.3957`；`0.5596/√6=0.2285`）⇒ 缺陷定位在词元层，不在解析/归属层（区别于 R407/R418 的「归属层错误」）。
- **交付**: `Tokenize` 否定标记（`不 没 未 无 非`）自身及其紧邻 1 个二元组带极性问题（`'\u0001'`；`Normalize` 丢弃全部控制字符 ⇒ 真实文本不可产出 ⇒ 无碰撞）；**查询侧与文档侧同一个 `Tokenize`**（对称性铁律：只做词元身份区分，无查询侧特判）；`Render` 片段行补 `AppendLine`；`+6` 单测。（19/19）
- **真机两臂（L4，同 harness、逐字节相同语料 sha256 已录）**:

  | 查询 | 治疗臂 `/tmp/pub_r421` | 负控臂 = **R420 产物快照** `/tmp/pub_r420_pre` |
  |---|---|---|
  | `存在` | 3 命中（`0.5596`，两个真实正样本） | 3 命中（同） |
  | `不存在` | **0** | **3**（`0.3957`）← 缺陷 |
  | `外星词根zzq不存在` | **0** | **3**（`0.2285`）← 缺陷 |
  | `zzq` | 0 | 0 |

  `llm_call` 两臂全查询 **0**；每查询 `recall_query` 恰 1；语料跑后**未被写**。13/13 判据 PASS。
- **两个仪器缺陷（都是「读数不可信」类，不是被测不达标）**: ① `Render` 把命中行与片段**粘成一行** ⇒ 任何按行解析的读数**只能取到第 1 条**（本轮 harness 第一版就这么把治疗臂读成 1 命中）⇒ 补 `AppendLine` + 单测「行可寻址」；② R420 记录的「`存在`/`不存在` 分数同为 1.5660」**不可复现**（实测 0.5596 vs 0.3957；真正相同的是**命中集合**）⇒ 口径更正，结论不变。
- **全量套件**: 1176/0/0（第 3 次跑）。**同一套件前两次各出 1 条顺序/并行相关假红**（`TelemetryPendingTests`；把本轮改动 stash 掉的**基线跑**里则是 `FrontendHandshakeTests`）⇒ 假红与 R421 无关，但「全量绿」这一读数目前**不可一次性复现**，登记为仪器候选。
- **诚实边界**: 极性作用域仅「否定标记 + 紧邻 1 个二元组」（句中远距否定未测）；`别/勿/莫/甭` **有意排除**（`别` 与 `识别/区别/特别` 碰撞）；`无/非` 复合词（`无线/非常`）碰撞致召回损失**未量化**；**打分无长度归一 ⇒ 同一词元命中的所有文档同分（本轮三份同为 0.5596），命中集内无相关度区分度**（登记 R422）；样本 3 文档/4 查询非分布；**主线 KPI（r1 管道增益 / 一轮 token −30%）本轮未触碰**——`/recall` 是本地确定性指令，`llm_call==0` 恰说明它**不产生**远端调用（是不必要调用的抑制器，不是 token 下降的直接贡献者）。
- **计划/证据/登记**: `docs/plans/v0.42.0-r421-polarity.md`；`eval/capability/r421/README-evidence.md`（L4）；`docs/verification-registry.json` → `r421.recall-negation-polarity`；TaskPlan **24 节点**（补登 `dev-recall-wiring` + `dev-recall-negation-polarity`）。


## R431 — role 额外数据（成长经历）挂载进 r1 门判：可机检 + 有界 + 无截断

> 文档缺口声明：本文件条目止于 R421，R422–R430 的权威记录在各自 `eval/rover/rNNN/README-evidence.md` 与「能力」目录；
> 未在此补写（不凭记忆回填读数）。本轮起恢复逐轮追加。

- **因果链**: 用户令「利用 r1 对真假信息判别（记得要挂载 role 的额外数据）」→ 前置机检发现真机角色 `skeptic.rbin` 解出键为 `['id','name','profile','tokens']`（**无 growth 键**）且调用点 `JudgeTurnAsync(content, roleSeed, **null**, ct)` → 挂载在真实负载上是**空操作**（管道本身早已支持：`BuildPrompt` 内 `Clip(growthBlock,300)`）→ 本轮把 null 换成 `GrowthLedger?.RenderForPrompt()`，并让「挂没挂」由遥测读数直接判定，而非「代码里有这行」。
- **产出**: `src/agent/IndustrialAgentV2.cs`（挂载点 + 4 项形状遥测 + `role_growth_domains`）；`src/agent.modelqueue/ModelQueueRouter.cs`（prompt 只构造一次，形状取自实发文本）；`src/agent.modelqueue/LocalGenerationPort.cs`（`TurnGateCounters.LastPromptChars/LastRoleSeedChars/LastGrowthChars/LastGrowthLines`）；`src/agent.roles/RoleGrowthLedger.cs`（`DomainCount`）；`src/agent.tests/TurnGateGrowthMountTests.cs`（**9 条**机检）；`docs/plans/v0.52.0-r431-growth-mount.md`；`eval/rover/r431/`（precheck/frozen_baseline/settle_r431/make_evidence + 双臂读数）。
- **基线对比**（同二进制 `sha256 ac62a739…`，字节 15,184,624，**IL 告警 0**，V0 形态闸 PASS）:
  | 臂 | 启动域数 | 门判 prompt_len | growth_chars(行) | 判定 | 远端调用 | 远端 tokens | 闭合/截断 |
  |---|---|---|---|---|---|---|---|
  | `-g431` 挂载（fixture 3 域） | 3 | `[426,426,426,426]` | `[70,70,70,70]`(3) | Skip×4 | 1 | 2030 | true / 无 |
  | `-b431` 对照（真角色 0 域） | 0 | `[355,388,388,388]` | `[0,32,32,32]`(1) | Skip×4 | 1 | 1994 | true / 无 |
  | R430 基线（挂载前） | — | 无该字段 | 0（未挂载） | Skip×4 | 1 | 1996 | — / — |
  测试(对侧 r431 节原记): 新增类 9/9；**全量 1251/0/0**（第 2 次跑；第 1 次 1250 通过 + `TelemetryPendingTests` 1 红，单跑 2/2 通过 ⇒ R421 已登记的仪器假红，与本轮改动无关）。
- **关键读数**: prompt 长度差恒等于 `块长+1`（挂载追加一个换行）—— 单测不变量与真机读数一致（355+70+1=426）；对照臂第 2 次门判起出现 32 字符/1 行，来自链自产账本（`IndustrialAgentV2.cs:1684`）⇒ 接线消费的是**链自己积累的**角色数据。
- **诚实边界**: **本轮不宣称 token 下降**（`k8r` 是重复认可族，本不产生额外远端调用；2030/1994/1996 同量级）—— ≥30% 验收需**真假信息判别网格**（假信息/纠错族），未跑；「有成长域时 r1 判得更准」**未测**（只测了生效/有界/不截断/判定不翻转）；`role_growth_domains` 仅启动配置行读一次，运行中新增域看 `growth_chars_seq`；对照臂 = 「角色无域」而非「代码不挂载」（干净对照是 R430 基线的 null 路径，已由引擎复算逐位证明）。
- **下轮候选**: ① 真假信息判别网格（P 族假信息/纠错），量化挂载对判定准确率与远端调用数的影响（≥30% 验证主战场）；② 遥测补 `growth_sha16`，把未挂载臂「同长」升级为「同指纹」；③ `role_growth_domains` 逐轮携带。
- **计划/证据/登记**: `docs/plans/v0.52.0-r431-growth-mount.md`；`eval/rover/r431/README-evidence.md`（L3）；`docs/verification-registry.json` → `r431.gate-role-growth-mount`。

## R434 — 前置门质量硬线: 「真假判别网格」P 族 + r1-Skip 双条件结构修 (2026-09-14)

- **因果链**（按文档走）: `docs/improvements.md` R431 节「下轮候选 ①」逐字指定「真假信息判别网格（P 族假信息/纠错），量化挂载对判定准确率与远端调用数的影响（≥30% 验证主战场）」 ⇒ 本轮预注册 `docs/plans/v0.55.0-r434-falseinfo-discrimination-grid.md`（判据 C1–C7）后执行。**机检前提**: 机械前置门把「?/问句词/诉求词/纠正词/数字/≥24 字符」全部结构性 Pass ⇒ r1 **只在残余带（无机械信号的短消息）判别** ⇒ P 族题集 8 个测量轮全部落在带内（机检 8/8 `MechanicalPass=false`）。
- **产出（分相）**:
  - Phase 1 基线（AOT `/tmp/pub_r434`, HEAD `69d405c`, IL=0）: 分母臂 A = 8 主答调用/**18493 tok**; 治疗臂 B(挂载域=3) = 2 主答调用/**4958 tok**（**降幅 73.2%**）; 对照臂 B0(域=0) 9535; 无设备臂 BP 19465（跳过 0）；复跑臂 B2 与 B **逐位一致**。
  - **质量硬线失守**: 4 个真诉求轮里 **3 个被 r1 判 Skip ⇒ 用户拿到空话**（`再讲一遍。`/`讲细一点。`/`从头再说。`）⇒ C2 ✗。
  - Phase 2（少样本修）**被实测证伪**: 门判两条 P 例 `另外，测试命令是什么？`/`不对，你上一轮不准确，请重新确认。` **全带机械信号**、生产里到不了本门 ⇒ 带内只剩 S 例 ⇒ r1 学成「短消息 ⇒ S」。补两条带内 P 例后 prompt 实测 +28 字符（425→453）但臂 B 判定**逐位不变**（B0 由 0.625→0.875）⇒ 不作修法。
  - Phase 3（**双条件结构修**，定稿 AOT `/tmp/pub_r434d` sha `54e30c19…`, IL=0）: `Skip 生效 ⇔ r1 判 Skip ∧ MechanicalAck(用户原文)`，非认可族一律降级 `Pass`（`gate:skip_rejected_nonack→remote`，新增 `SkipRejected` 计数 + `local_turn_gate_reject` 事件）。方向性 = **白名单**（承认哪些可省）⇒ 任何误判只可能多花 token，**不可能让真诉求变空话**。
- **基线对比**（同网格 `task-p8`；外部真值 = 桩逐请求 tokens + 逐轮回复来源；内容锚定+顺序分区 `unassigned=0`；通道分离 G 主答/J 判官）:
  | 臂 | 主答调用 | 判官调用 | 总 tok | 相对 A | 假阴性 | 假阳性 | 判定准确率 |
  |---|---|---|---|---|---|---|---|
  | A 门关（分母） | 8 | 0 | 18493 | — | — | — | — |
  | B 挂载（域3）修前 | 2 | 7 | 4958 | 73.2% | **3** | 0 | 0.625 |
  | **B 挂载 修后** | 5 | 7 | **12338** | **33.3%** | **0** | **0** | **1.000** |
  | B0 未挂载 修后 | 5 | 7 | 12163 | 34.2% | 0 | 0 | 1.000 |
  | BP 无设备（负控） | 8 | 7 | 19465 | -5.3% | — | — | 跳过 0 次 |
  | BRJ 单变量（判官本地优先） | 5 | 6 | 12288 | 33.6% | 0 | 0 | 1.000 |
  | **扩族 task-p12**（12 轮, 含带内假断言/带外假断言/纠错）A | 11 | 0 | 27670 | — | — | — | — |
  | 扩族 task-p12 B（挂载） | 7 | 8 | 19990 | **27.8%** | 0 | 0 | 1.000 |
  判据: C1 ✓（IL=0；两外部真值通道；带内机检 8/8）/ **C2 ✓（假阴性 0）** / **C3 ✓（假阳性 0）** / **C4 ✓（33.3% ≥ 30%）** / C5 ✗（挂载无增益，且压制示例敏感度） / C6 ✓（无设备 ⇒ 跳过 0） / C7 ✓（逐位复现）。
- **测试状态（R434 定稿）**: 全量 **1267 项 / 1266 绿 / 1 红** —— 红项 = `TelemetryPendingTests.Emit_Before_Configure_Is_Flushed_On_Configure`（**已登记仪器假红**: `AgentTelemetry` 为静态类 + 测试类并行 ⇒ Configure 顺序竞态）; 单跑该类 **2/2 绿**; **排除实验**: 以 `--filter FullyQualifiedName!~产物遥测键契约` 复跑仍 1 红 ⇒ 与本轮改动**无因果**（不是本轮引入）。
- **机器不变量（新增测试）**: `G30` 门判示例**每个 tag 至少一条落在残余带内**（带外示例对 r1 不可见）；`G31` 认可族判定表（正向 5/反向 8，含「再讲一遍。」族）；`G32` 链侧必须接线。对侧冻结基线与 R434 重冻结留痕（355/`8749b0a1…` → 383/`2dcfe801…`，+28 逐字节可核）。
- **诚实边界**: ① 单机单次（除 B 的两批复跑）；② **代价已披露**：质量硬线恢复使降幅由 73.2% 降到 33.3%（换掉「错跳真诉求」的省法）；③ C5 挂载贡献为负/无 ⇒ 本族**不宣称挂载增益**；④ 认可族白名单保守 ⇒ `好，按这个来。` 这类带内真·认可也会走远端（只多花 token）；⑤ **J 通道（更正）**: 关系判官本地优先，但 `local.relation_judge` **默认 false** ⇒ 默认远端（本轮臂全为 false，8 次判官全部 remote ≈341–375 tok）；单变量臂 **BRJ**(=true) 实测 8 次判官仅 **1 次 local 成功**、**6 次 remote_fallback**（字母取到桩文本）⇒ 「J 本地化」**未达成**；桩不产出合法字母 ⇒ J 的**收益**在本器具下不可测，只报开销；⑥ 轮 4（`好的，明白。`）在**全部臂**被产品澄清 ask 消费 ⇒ 测量轮 = 8 而非 9；⑦ 单族 8 轮，外推需另跑；⑧ 门判遥测 `basis` 已改为反映**最终判决**（修前会写 r1 原始判决 ⇒ R433 同类「读数自报假形态」风险消除）。
- **候选推进台账（用户令: 所有候选无疑问则全推进）**: ① 双条件结构修 **达成**；② 门判示例带内不变量 **达成（结构）**；③ 挂载增益 **负结论**；④ J 本地化 **未达成**（local 1/7）；⑤ 门禁复位（对侧 R431 行）**达成**（全量 1266/0/0）；⑥ TaskPlan 回填 R430–R434 **达成**（30→35 节点）；⑦ 题集扩族（`task-p12`, 12 轮含带内假断言/带外假断言/纠错）**达成（含负结论）**: 质量判据全绿（假阴性 0 ∧ 假阳性 0 ∧ acc 1.000, 带内假断言被双条件救回）但 **降幅 27.8% < 30%** ⇒ 主判据在低认可占比题集上不成立（预注册 §14 已列风险）⇒ 宣称收窄「≥30% 依赖认可轮占比」，**未调题集凑数**；⑧ `code_source`/产物通道**达成（契约钉死）**: 生产端与判分端两侧机检测试（`script_artifact` 的 path/compile_valid/origin/sha8/exit + `grade.py` 消费点），防 R433 假红重生。
- **下轮候选**: ① J 判官 prompt 可解析性（本地 1/7 的根因: 查 raw/error，或改判定形式/预算）——「不必要的 API 请求」最大残余；② 认可族白名单扩容（`好，按这个来。`/`照你说的办。` 等），须以**成对判据**（假阴性=0 ∧ 假阳性=0）为准；③ 题集扩族（假信息断言/多轮纠错/跨域）以检验外推；④ R433 遗留 `code_source`/产物通道写入产品侧遥测契约；⑤ 门禁/登记表复用（本轮已复位对侧 R431 行 `evidence_path`/`covers`）。
- **计划/证据/登记**: `docs/plans/v0.55.0-r434-falseinfo-discrimination-grid.md`；`eval/rover/r434/README-evidence.md`（L3）；`docs/verification-registry.json` → `r434.turn-gate-double-condition`；`eval/capability/kpi.jsonl` 末行 R434。


### R435（2026-09-14）关系判官（J 通道）本地化：真机 1/7 → 5/6

- **用户令（逐字）**: 「利用r1对真假信息判别…让用户一轮任务总数tokens使用量显著下降30%以上(主要是不必要的llm api请求少了)」⇒ 本轮攻 R434b 负结论「J 本地 1/7」= 不必要远端调用最大残差。
- **推进台账（用户令: 所有候选无疑问则全推进）**: ① prompt 形状（承重）**达成**: 本地可解析 1/6 → 5/6（真机 6 例，非空 prev），远端判官调用 6 → 1；② 失败原因遥测 `local_state` **达成**（R434 归因缺口闭环）；③ 空 `previousReply` ⇒ 结构性 Neutral **达成**（确定性规则，0 模型调用，消掉 turn1 的必失败例）；④ 解析层加固（64 字尾窗 + 判定词表 + 负控）**达成但非承重**（四臂 old≡new）；⑤ 预算 512→1024 **负结论（已回退）**（A1≡A2、A5≡A4 逐例相同，turn5/turn9 在 1024 仍耗尽 67.8s）；⑥ 端到端 token KPI（≥30%）**未测** ⇒ 下轮承重。
- **方法学要点**: ① 先取证: 产品遥测 8 条 + 忠实探针 A0 复现 1/7（**耗时逐例对齐** 18.09↔20.407s…9.76↔9.894s，pred=149=tokens=149）⇒ 器具可信后才改码；② 单变量六臂矩阵（prompt 形状 × 预算 × 解析层）；③ 反教考同一: v2 实例**不用 grid 原句**；④ prompt 单一构造点 `BuildJudgePrompt`（本地/远端同一输入面，结构上不可能两套提示）。
- **自纠（必须披露）**: 探针 think 标记手打混入 **U+200B** ⇒ `close` 恒 False ⇒ 分类器读思考链 ⇒ 假阳性 8/9（与产品 1/7 冲突暴露）；改由**源码程序化派生 + 长度/码位断言**。另: 同会话覆盖未 commit 的计划案 ⇒ 原 pre-registered 阈值不可恢复，相关阈值改标 `checks_posthoc`。
- **下轮候选**: ① **端到端 BRJ 网格重跑**（新 AOT 二进制）测 ≥30% token 判据（承重）；② turn9 类「思考链无界」（停发词/思考长度约束）；③ turn7 类 A/N 边界（同族实例）；④ 门+判官**合并单次本地调用**（省一次 prefill，性能向）。
- **计划/证据/登记**: `docs/plans/v0.56.0-r435-relation-judge-localization.md`；`eval/rover/r435/`（probe_j1..j4 + reclass_j2 + probe-j{2,3,4}-classified.json）；`src/agent.tests/RelationJudgeParseTests.cs`（18/18）；`eval/capability/kpi.jsonl` → R435。

### R436（2026-09-15）端到端 BRJ 网格重跑：承重 token 降幅 29.28%（p12）/ 34.41%（p8）

- **用户令（逐字）**: 「利用r1对真假信息判别…让用户一轮任务总数tokens使用量显著下降30%以上(主要是不必要的llm api请求少了)」⇒ 本轮承重 = R435 新 AOT 二进制端到端重跑（R435 §7 候选①）。
- **推进台账（用户令: 所有候选无疑问则全推进）**: ① **端到端 BRJ 网格重跑（承重）达成（含负结论）**: J 本地化自 R434 登记 **1/7（本地成功）** 提升至 **7/7 全本地**；远端判官请求 `7` 次 → **0**；p12 降幅 27.8% → **29.28%**（+1.48 pt）但 **< 30.0%**（差 0.72 pt）⇒ 承重未达；p8（可跳散布）=34.41%（达标）；② 判据 C1–C8 逐项机器判定（`verdict-summary.json`）**达成**；③ 器具加固: J 标记**程序化派生**（源码字面量 + 无不可见码位断言）替代手打（R435 U+200B 教训）**达成**；④ 归档复现控制 S1（同标记重跑 R434 五份 calls ⇒ G/J 计数逐臂一致）**达成**；⑤ 确定性复跑（BRJ#2 Δtoken=7）**达成**。
- **基线对比（同二进制 sha16 `45c37dd5b88ffcf2`；外部真值 = 桩逐请求 tokens + 遥测双源；通道分离 G 主答/J 判官）**:

  | 臂（task-p12） | 主答调用 | 判官远端 | 判官本地 | 总 tok | 相对 A | 假阴性 | 假阳性 | acc |
  |---|---|---|---|---|---|---|---|---|
  | A 门关（分母） | 11 | 0 | 0 | 27654 | — | 0 | 4 | 0.6363636363636364 |
  | B 门开+J 远端 | 14 | 7 | 0 | 20633 | 25.39% | 0 | 0 | 1.0 |
  | **BRJ 门开+J 本地** | 7 | 0 | 7 | **19557** | **29.28%** | **0** | **0** | **1.0** |
  | BRJ#2 复跑 | 7 | 0 | 7 | 19564 | — | 0 | 0 | 1.0 |
  | BP 无设备（负控） | 18 | 7 | 0 | 29569 | -6.92% | 0 | 4 | 0.6363636363636364 |
  | p8: A → BRJ | 8 → 6 | 0 → 1 | 5 | 18481 → 12122 | **34.41%** | 0 | 0 | 1.0 |

- **降幅分解（同二进制, 单变量）**: 门（跳过 4 个早簇认可轮）= A→B 25.39%；J 本地化（消除 7 次远端判官调用）= 1083 tok = 3.92 pt ⇒ 合计 29.28%。
- **自纠（必须披露）**: ① 本轮 settle 器具首发崩溃（归档 verdict 字段名 key 缺失）⇒ 修脚本 + **离线重结算**（原始 calls/遥测全部在盘, 未重跑臂）; ② S2 交叉定义首版错误（把 `source!=local ∧ prompt_len==0` 的**结构性判定**当成远端请求）⇒ 按实测分类学收紧为 `prompt_len>0`; ③ AOT 发布**非逐字节可复现**（同源两次发布差 325 字节, BuildID 不同）⇒ 二进制 sha 不可当源码状态指纹; ④ 本侧发布窗与对侧 60m 自检作业（23:55 写 R437 分析行）重叠 ⇒ 已登记, 未改他方产物。
- **诚实边界**: ① 远端 token 为**桩侧估算**（非真实计费）; ② 未真机重放远端（桩返回固定话术 ⇒ 臂 B 的远端判官字母无意义, 故 B 的 acc 不代表真机）; ③ 本地判官 1301 tok（7 次）不计入 API token 但非零成本（串行 139 s）; ④ ≥30% **未**在 p12 达成 ⇒ 宣称收窄「≥30% 依赖可跳轮占比**与位置**（早簇最不利）」。
- **对侧交叉（R437 模型, 不改他方产物）**: 对侧 R437 预测 J 修复 +1.1…+1.9 pt（p12 28.8–29.6）⇒ 本轮实测 +1.48 pt **落在该带内**。
- **下轮候选**: ① V1–V5 长度分档实测（对侧 R437 §7 已预注册; 需先空出测量窗）; ② p12 型早簇构成下要 ≥30% ⇒ 降单次主答 prompt（上下文/记忆段按轮压缩 或 role 块瘦身）; ③ turn9 类「思考链无界」（R435 遗留）; ④ 门+判官合并为单次本地调用（省一次冷启动）。
- **计划/证据/登记**: `docs/plans/v0.57.0-r436-e2e-brj-token-kpi.md`；`eval/rover/r436/README-evidence.md`；`docs/verification-registry.json` → `r436.e2e-brj-token-kpi`；`eval/capability/kpi.jsonl` → R436。

## R439 — 修复的域扩展验证：长任务 V20(20 轮) + p8 复测（零源码改动）

- **承重读数（远端 API token 降幅）**：p8 37.9%（严口径 G+J；G 口径 38.74%）、**V20 45.31%**（G 口径 45.81%）、p12 37.37%（R438）。三条网格 ≥30% ⇒ R438 修复非 p12 特例，且**降幅随任务长度上升**（长网格 45.3%）。
- **口径纠正（诚实登记）**：R436 台账 p8 的 34.41% 用「G+J」总量计；判官本地化口径下 **G-only=38.74% / 严口径=37.90%**（pre-fix G-only 为 35.25%）。修复本身贡献 +3.49pt（p8）。
- **预注册 → 实测**：跑前预测（01:51 落盘）p8 39.28% / V20 42.37%；实测偏差 **−1.38pt / +2.94pt**（均 ≤3pt 容差）。A 臂跑完后锚定预测 V20 45.37% → 偏差 −0.06pt（**该文件被 cp 覆盖后于 02:13 重生成，时序证据弱化，已登记在案**）。结构模型（A 逐调用曲线 + 角色块偏移 δ(i) + 跳过块质量 m(t)）在**真外样本** p8 上复现 BRJ 总量偏 0.73%（p12 0.0%）；V20 分母外推只差 −0.4%。
- **门质量**：p8/V20 fn=0, fp=0, acc=1.0（7 个 ack 轮全跳 / 13 个带内真诉求全通）⇒ 省钱没有靠错杀真诉求换来。
- **A 臂分母不变性**：p8 A 复跑 = R436 = 18481 tok（逐位相同）⇒ 对比可跨轮使用。
- **诚实边界**：无设备负控(BP)本轮未跑（V20 净增量未测，沿用 R438 p12 −6.92%）；BRJ 同臂复跑未做；桩外部真值不含 provider 缓存/计费；V20 判官本地成功率 11/13（2 次远端回退 310 tok，已计入）。
- **器具**：`eval/rover/r439/{predict_r439.py,design_check.py,agg_r439.py,run_all.sh,grid/task-V20.json}`；设计审计器为 Python 第二实现，对 p8/p12 的机械判定与 C# 实测逐轮全等（自证）；证据档 `eval/rover/r439/README-evidence.md`。

## R438 — 本地消化轮不得回放「从未发出的」内联块（缺陷修复，p12 越线 37.37%）

- **因果链**: `IndustrialAgentV2.cs:1267` 在**门判定之前**无条件 `message.SentContent = sentUserContent`（含本轮内联块）
  → 门判 `Skip` 的轮次**没有任何远端调用**（块从未离开本机）→ `GetConversationHistoryAsync:2670` 按 `SentContent ?? Content`
  把它落进会话历史 → 此后**每一次**远端调用都逐字回放这些从未发出的块。修复 = 跳过分支把 `SentContent` 归位为 `outboundText`。
- **缓存红线为何不受影响（先拆前提）**: R379「发送字节=回放字节」的语义域是**已发送字节**；本地消化轮无发送字节，
  其条目位于 provider 已缓存前缀**之后** ⇒ 剥离不改变任何已缓存字节。
- **臂矩阵（p12, 12 轮, 同一 AOT 二进制）**:

| 臂 | 调用 G/J | r1 skip | AOT token | 降幅 vs A | FN/FP/acc |
|---|---|---|---|---|---|
| A 关闸基线 | 11/0 | 0 | 27654 | 0.0% | 0/4/0.636 |
| **BRJ 门+J本地+修复** | 7/0 | 4 | **17319** | **37.37%** | 0/0/1.000 |
| BRJ2 同臂复跑 | 7/0 | 4 | 17326 | 37.35% | 0/0/1.000 |
| BP 无设备负控 | 11/7 | 0 | 29569 | −6.92% | 0/4/0.636 |

- **预注册命中**: `predict_r438.py`（逐字节重放 R436 冻结 calls + 同估算器）预测 **37.37%**，实测 **37.37%**（偏离 0.0 pt）。
- **因果归因**: 同臂 BRJ 相对 R436 档案 19557 → 17319 = **−2238 tok**，且逐调用 token 差与「条目字符差/2」最大偏离 **0.0** ⇒ 全部差异就是被移除的块。
- **不变量机检（新器具）**: 相邻远端调用「前一次请求是后一次的逐字前缀」— A 10/10 对、BRJ 6/6 对、**0 违例**（把 R379 红线从注释变成判据）。
- **泄漏形状**: BRJ 跳过轮 [2,3,4,5] 泄漏块 = **0**，24/24 条目逐字等于机检派生的用户原文；臂 A（无跳过轮）逐调用读数与 R436 **完全相同** ⇒ 无附带效应。
- **确定性**: Δ=7 tok（0.040%），残差**完整归因** = 系统提示内嵌 run 目录路径长度差 2 字符（非模型抖动）。
- **自纠（必须披露）**: ① verify 首版 C6 过严（把「首轮无前序上下文 ⇒ 块为空」误判为缺块）⇒ 加首轮免检并用 R436 档案反证该豁免**先前就存在**（A 11/11、BRJ 7/7 首轮条目无块）; ② 首版 C7 要求逐调用读数全同（真机本地生成回复长度可变）⇒ 改「决策全同 + Δ≤0.5% + 残差可归因」。
- **诚实边界**: ① 远端 token 为**桩侧估算**非真实计费; ② 未真机重放远端; ③ **本轮未跑 p8**（承重已由 p12 达成，p8 属外推）; ④ 前缀单调性只覆盖桩侧请求序列，**provider 真实命中率未测**; ⑤ 本地 r1 成本 1301 tok/139 s 串行不计入 API token 但非零。
- **下轮候选**: ① p8 + 长度分档 V1–V5 复测（≥30% 的域扩展）; ② 排查其它零远端调用路径是否仍写 `SentContent`; ③ 门+判官合并为单次本地调用（省一次冷启动，R435 遗留）; ④ turn9 类「思考链无界」。
- **计划/证据/登记**: `docs/plans/v0.58.0-r438-localskip-no-replay.md`；`eval/rover/r438/README-evidence.md`；`docs/verification-registry.json` → R438；`eval/capability/kpi.jsonl` → R438。
