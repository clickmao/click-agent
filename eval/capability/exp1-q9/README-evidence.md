# EXP1-Q9 证据说明: 弱边接入「文档→代码」引用图分类 + 弱边**全量**抽检 (25/25)

- 轮次: **EXP1-Q9** (本侧 60m 自检作业; **不占主线轮号** —— 对侧 30m 主线作业当时在跑 `R443` 的 `dotnet publish`)
- 目标计划项: `docs/plans/v0.22.0-longterm-backlog.md` 最前未完成项 = 附录 I.9 候选 #1
  (「把 25 条弱边接入引用图分类 (强边 `declared_*` / 弱边 `*_mention`), 且**先把弱边交人工抽检**」)
- 证据等级: **L1-static** (真跑仪器 + 真跑抽检器; 无编译/单测/AOT/真机运行) —— 不得报 L3/L4
- 本轮**零产品源码改动**、**不跑 dotnet**(对侧在真机 publish 窗口)、零 `skills/`、零登记表改动

## 1. 因果链

1. I.9 候选 #1 连续一轮挂账: 弱边轴 (v2.4.0 阶梯) 已能**识别** 25 条弱边, 但 (a) 没有接入引用图的**边强分类**,
   (b) 只抽检 4/25 (skill 原则 3: 写断言前必须查真实输出样本) ⇒ 结论悬空。
2. 本轮只推**一步**: 仪器 v2.4.1 → **v2.5.0** 增「边强轴」(强边 `declared_*` / 弱边 `*_mention` / 断边 `absent` / 弃权),
   并对两套口径各做**全量**抽检 (A 符号级 25/25、B 引用级 16/16)。
3. 抽检结果**改了结论的用户面**: 25 条弱边里 **20 条是「名字类事实」**(telemetry 事件名 / JSON 协议键 /
   环境变量名 / 路由常量值) —— 这类名字在代码里**天然只以字符串或注释形态存在** (环境变量名永不在代码里"声明",
   遥测事件名永远是两个引号包起来的 `Emit` 首参) ⇒ 若把弱边并入「缺陷/断边」桶, 会把 20 条**引用正确**的条目误判成引用问题
   (虚增 20 条 = 62 条弱边的 32%)。
4. 同时暴露 **2 条真候选**(A18 `_queryEmbedding`、A19/A25 `RegisterCapability`): 主判据 (全文匹配) 看不见的
   「引用目标已被移走/名字已漂移」, 只有弱边轴可见 ⇒ 弱边轴的**实际价值**在此, 而非在"标红"。

## 2. 产出表 (全部真跑)

| 产出 | 路径 | 读数 |
|---|---|---|
| 预注册判据 (测前落盘) | `prereg_q9.json` | B1–B8 + 定义 + 排除项 |
| 定版补丁 | `patch_v241_to_v250.py` | 15 条锚点替换各断言命中 1 次; 源 sha `8e26787d…` → 目标 sha `eded7ab0…`; `patch_pins.json` |
| 仪器 v2.5.0 | `probe_v250.py` | 真跑 6.7s, `exit 0`, **G1–G8 全过** |
| 主读数 | `attribution_q9_edges.json` + `citations.jsonl` | 939 条引用 / 180 文档 / 596 只读输入 |
| A/B 不改判 | `ab_edges.py` → `ab_edges.json` | `verdict_diff=0` / 既有字段 `field_diff=0` / 旧侧新字段 0 / 守恒 / 两跑逐位相同; `exit 0` |
| 弱边全量抽检 | `weak_edge_inspect.py` → `weak_edge_table.json` / `.md` | A 25/25、B 16/16、全 check 绿 (`inspect_stdout.json`) |
| 仪器自检 | `selftest_v250.json` | **71/71 绿** (含新增边强轴 E1–E17), `exit 0` |

## 3. 基线与读数

**语料**: 180 文档 / 596 只读输入逐文件 sha256 / **939 条引用** (Q8 为 179/595/939 ⇒ 文档 +1, 语料移动目标)。

**引用判据桶面 (与 Q8 逐位相同, 本轮零改判)**: `ok 753` / `symbol_absent 66` / `waived 70` / `stale_lines 4` / `retired 21` / `stale_path 8`。

**新边强轴 (v2.5.0; 分母 = live 代码引用 922 条)**:

| 档 | 数 | 含义 |
|---|---|---|
| `strong` | 363 | 至少一枚被引符号在该文件里**有声明** (`declared_*`) |
| `weak` | 62 | 无声明但有符号**出现** (`*_mention`); 子级 `weak_code 46` / `weak_noncode 16` |
| `broken` | 38 | 全部符号在该文件查无 |
| `waived` | 459 | 引用未解析/不可剥离/本身 waived ⇒ **弃权, 不进分母** |
| 和 | 922 | == live 代码引用数 (G8 守恒闸) |

`n_edges_strong_with_weak_symbols = 12`: 强边里混着弱符号的引用**可见** (最强胜聚合不吞信息) —— 若只看聚合档,
这 12 条会被读成"纯强边"。

**弱边全量抽检 (两口径, 单位不同不可换算)**:

| 口径 | 单位 | 全量 | 上下文行 |
|---|---|---|---|
| A (计划口径) | 符号级 `noncode_mention` ∧ `verdict=ok` | **25** (== 计划里的「25 条弱边」) | 43 |
| B (引用图口径, 本轮新增) | 引用级 `weak_noncode` 边 | **16** | 35 |

A 的 25 条按**机器可提取的证据**分类 (每条都有上下文行, 见 `weak_edge_table.md`):

| 类 | 数 | 判据 (可机检) | 例 |
|---|---|---|---|
| 名字类事实 | 20 | 名称形态 `snake_case`/`SCREAMING_SNAKE` + 出现面 = 字符串/注释 + 树内无声明 (env/键名**不可能**有声明形态) | `req_id`(JSON 键)、`loop_turn`(遥测事件名)、`AGENTFRAMEWORK_PY_RUN`(环境变量名)、`verify_local`(`const string` 的**值**) |
| 跨文件指代 | 3 | `declared_elsewhere_files >= 1` (符号真身在别的文件) | `VulkanNames`(真身 `src/agent.gpu/VulkanNames.cs`)、`NullTextEmbedder`、`OpenAILLMCaller` |
| 注释里的历史/漂移符号 | 2 | PascalCase + 树内零声明 + 仅在注释 | `_queryEmbedding`、`RegisterCapability` |

**弱边 ≠ 缺陷的量化依据**: 25 条中 22 条 `declared_elsewhere == 0`, 但其中 20 条属于**天然无声明形态**的名字类事实
(环境变量名 / JSON 键 / 遥测事件名) ⇒ 「弱边」是这类引用的**正确表示**, 不是缺陷标记。

## 4. 诚实边界

1. **L1 静态机检**: 全链离线复算 (`importlib` 同进程加载两版模块 + 只读文件), **无编译/单测/AOT/真机运行**。
2. **词法级非 AST**: 边强由注释/字符串剥离 + 声明形态正则派生; `weak_code` 里的"调用点"与"声明"在裸 `Sym(` 形态下不可区分
   (宁漏勿错), 撇号误吞等已知近似同 Q8。
3. **只回答「在被引这一个文件里的形态」**: 弱边**不等于**引用错误 (20/25 已实证); 本轮**没有修好任何一条引用**。
4. **两口径单位不同**: 25 (符号) 与 16 (引用) 不可互相换算; A 落进 B 的覆盖率为 17/25 (另 8 条的宿主引用因含 `code_mention`/
   `absent` 符号被归到弱码面/断边) ⇒ 并列报数, 不合并。
5. **`declared_elsewhere` 是旁证不是判据**: 只扫 `src/**/*.cs|*.py` (排除跳过目录), 不解析跨项目引用/部分类 ⇒ 计数是**下界**。
6. **形式校验 (`VerificationForm`/`SkillGeneralization`/`DevPlanDocRef`) 本轮未跑**: 对侧主线作业当时正在
   `dotnet publish … -o /tmp/pub_r443` (真机 AOT 窗口) ⇒ 按并发纪律本侧不跑 dotnet; 且改动面 = `eval/` 探针 +
   两份计划文档, **未触及** `docs/verification-registry.json` 与 `skills/` ⇒ 触发器未命中, 列为**对侧空闲后即跑**项。
7. **语料是移动目标** (对侧在改 `src/`/`docs/`): 读数绑定当轮语料, 由同进程 A/B + 逐文件输入 sha256 消解。
8. **本轮自捕 (测量层)**: 抽检器首版把「弱边内**每个**符号都要有上下文行」写成判据 ⇒ 混在弱边里的 `absent` 符号
   (按定义无出现行) 让判据假红 2 例。修法 = 预注册判据按**边**判 + 事后补检按 **`*_mention` 符号**判 (`checks_posthoc`),
   `absent` 符号单独断言"无上下文行"。属判据实现缺陷, 非被测缺陷。

## 5. 下轮候选 (一步)

1. **把弱边再细分 (本轮数据已给出分界线)**: `weak_kind = named_fact`(名称形态 ∈ {`snake_case`,`SCREAMING_SNAKE`}) /
   `cross_file`(`declared_elsewhere >= 1`) / `comment_only`; 判据预注册 + 两侧夹具 (含"名字类事实不得被计入缺陷"负控)。
2. **2 条真候选的人工复核**: `_queryEmbedding`(注释明写"已消除"而主判据仍 `ok`) 与 `RegisterCapability`
   (注释宣称登记入口但树内零声明) —— 需到 `src/agent/registry/` + `ContextAssembler.cs` 核**真实方法名**, 属**文档时效**问题。
3. H.7 候选 #2 (计数守恒不变量升为仪器侧一等判据) 与候选 #1 (8 条 `same_commit_as_deletion` 语义裁定) 仍未做。
