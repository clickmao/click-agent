# R455 · agent 链机制诊断（外部参照 codex-cli）

状态: 已落盘（R455 套件测量进行中；本节为源码级机制证据，不依赖测量数字）

## 0. 用户裁定（驱动本轮）
1. 「像这种属于无效数据，你乱搞了6次更无效了，得同环境同输入，且输入能测得了agent功能每个模块效果如何，你一句话过去看不了命中率，又没测试到闸门，又给codex连续6次 破坏了返回对比基准」 ⇒ 单句对照作废（原 §7 已打 VOID 标记）。
2. 「这就属于有效对比，codex直接在轮内完成了用户的真实意图(问询次数kpi)而本agent还在问你要看哪个」 ⇒ 判据面新增**问询次数**（澄清轮次）。
3. 「你不应该考虑关键字或者其他布丁方案修补，我想目前是agent链上机制产生了问题」 ⇒ 禁关键字/提示词补丁，须修**链机制**。
4. 「可以将对比流程加入开发文档内」 ⇒ 对比器具升格为常态开发流程（见 `docs/external-reference-harness.md`）。

## 1. 事实（套件实测 R455，同环境/同输入/同模型 deepseek-flash/零重试）
| 模块 | 我方 click-agent | codex 0.154 |
|---|---|---|
| M4 执行（4 产物） | **0/4**（count.txt / merged.txt / stats.txt / first.txt 全部不存在） | **4/4**（`4` / `ALPHA\nBETA\nGAMMA` / `chars=14` / `R455 fixture note`） |
| 问询/澄清 | T6 直接反问「你想让 agent 做什么?」+ T1–T5 全部为「承诺/推断」 | 0 |
| 远端调用 | 7 次（6 轮） | 13 次（6 轮，含每轮 1–3 步动作） |
| token 面 | in 18,039 / cached 15,616 = **86.6%** / out 957 | in 91,002 / cached 87,936 = **96.6%** / out 597 |
| 请求面 | `messages` only，**无 `tools`** | `instructions` + **9 工具** |
| 闸门（M2） | 无 llama-server（内存闸 <2650MB）⇒ `n/a`（不记通过） | — |
| 幻觉动作 | T2「**已完成**：count.txt 写入」+ 伪命令行，**盘上无该文件**；T3/T4 断言 `x/y/z.txt` 不存在（实际存在） | — |


## 2. 机制根因（源码级）
### 2.1 上游请求无动作声明面
`src/agent.modelqueue/ModelQueueRouter.cs:950-1000 SerializeChatRequest()` 只写 `model` / `messages`（+`reasoning_effort`/`response_format`）。
⇒ 模型**没有结构化动作出口**；`grep -rn "tool_calls" src/`（全仓 *.cs）= **0 命中**（唯一命中是测试里的 `tools/py` 目录名）。

### 2.2 唯一执行入口挂在**用户输入**上，而非模型输出上
`src/agent/IndustrialAgentV2.cs:633-636`
```
if (_skillDispatcher != null && …)
    var skillResult = await _skillDispatcher.DispatchAsync(message.Content, ct);
```
⇒ 执行触发键 = **`message.Content`（用户文本命中技能路由）**。新任务（“数 .py 文件”）不命中任何技能 ⇒ 无动作可做。
⇒ **不存在**「模型输出 → 执行 → 结果回灌 → 再推理」的闭环（`_skillDispatcher` 在 V2 中仅 :633/:709 两处，均非模型输出驱动）。

### 2.3 后果链（与用户钦定 KPI 直接冲突）
可执行任务 → 无动作出口 → 模型只能产出**方案/承诺/澄清提问** → 用户必须再发一轮 → **轮数↑ ⇒ 远端调用↑ ⇒ 总 token↑**。
用户钦定 KPI = 「一轮任务总 token ↓≥30%（主要是不必要的 LLM API 请求少了）」⇒ 本缺陷是**KPI 的反向承重项**：`问询次数`（澄清轮）是可直接计量的上游指标。

### 2.4 为什么不能用关键字/提示词补
- 关键字补丁 = 把 2.2 的触发键从「技能路由」扩到「更多模式」⇒ 仍无 2.1 的动作声明面与结果回灌 ⇒ 模型依旧只能“说”。
- 提示词补丁 = 让模型「别问直接做」⇒ 无出口，只会把承诺话说得更像行动 ⇒ **空心**（用户审计口径：`llm:true` 空心 ⇒ 断言须绑定组件真实行为）。

## 3. 修复设计（链机制，非补丁）
**动作环（Action Loop）三件套**，全部走既有可替换执行面端口：
1. **声明面**：远端请求按能力注册表派生 `tools[]`（只读/写/执行三类，schema 手写或 STJ Source Generator；AOT 零反射）。
2. **解析面**：解析 `tool_calls`（AOT 手写 JSON，禁反射序列化），映射到既有 `SkillScriptRunner`/`GitOperations`/文件端口。
3. **回灌面**：把执行结果作为 `role:"tool"` 消息回灌，受限步数（N≤3）+ 每步落盘审计（命令、rc、stdout 有界截断），超限即收敛。
**KPI 归因**：动作环把「澄清轮」转为「轮内动作」，直接减少**用户可见轮数**与远端调用数；`问询次数` 作为一等指标入册。

## 4. 验收（待 R456 实施后测）
- A1 产物：四产物机械等值（count.txt=4 / merged.txt / stats.txt=chars=14 / first.txt）。
- A2 问询次数：同套件下我方澄清轮数 ≤ codex（目标 0）。
- A3 成本：一轮任务远端调用数 ≤ 基线（动作环不得增加轮数）；缓存命中率不退化。
- A4 铁律：AOT 零反射、发布形态自证、命令落盘审计、无关键字/提示词补丁。

## 5. 套件器具（同环境/同输入/逐模块可测）
- 夹具 `/tmp/r455_setup.sh` ⇒ `/tmp/r455_env/{codex,agent}/work`（a–d.py、x/y/z.txt、notes.md；两侧逐字节同）。
- 输入 `/tmp/r455_env/suite-turns.json` 6 轮：T1 数 .py 个数 / T2 写 count.txt / T3 合并 x+y+z→merged.txt / T4 数 merged 字母数→stats.txt / T5「继续」（闸门·吸收位） / T6 写 notes.md 首行→first.txt。
- runner `eval/rover/r455/run_suite.sh`：codex 单会话（`exec` + `exec resume`，**进程 cwd 必须=夹具目录**——实测 resume 不沿用记录 cwd，是首跑“cwd 漂到仓库根”的根因）；我方单会话 6 轮（`--frontend-api 48616`）。
- adapter `eval/rover/r455/adapter_tools.py`（48615）：透传 codex `tools`、chat `tool_calls`→Responses `function_call`、`response.completed` 必须带 `input_tokens`/`output_tokens`（否则 codex 自行重连 ⇒ 破坏基准）。
- 判分 `eval/rover/r455/judge_suite.py` **只读落盘证据**；预注册 `prereg-r455.json` 只声明结构性不变量。
- 逐调用真值：adapter 落盘 `side-{agent,codex}-*.json`（含上游 usage 原样）。

## 6. 判定
- **R455 = 有效对照（满足用户三条件：同环境 / 同输入 / 逐模块可测）**：M1 缓存、M2 闸门（本轮 `n/a`+成因）、M3 吸收、M4 执行、M6 token 五格全部给出可复核数字。
- **结论**：我方 0/4 产物 + 1 次直接问询 + 4 处伪造执行记录；codex 4/4 产物 + 0 问询。⇒ 主因 = §2 的无动作环，**不是模型能力差异**（同模型同输入）。
- **KPI 口径提示**：token 总量在两侧不可比（静态面/工具面不同源）；「省 token」只有在**任务完成**的前提下才有意义 ⇒ 先修动作环，再谈降幅。
- **post-hoc 修正（非判据变更）**：首判 `merged.txt` 因判分器未对被期望值归一（`norm(exp)`）而记 FAIL，代码事实为 `ALPHA\nBETA\nGAMMA` 正确 ⇒ 修判分器一行后 codex 4/4。
