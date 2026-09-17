# R524 —— 提示词前缀纪律（常量前置 / 易变后置 / 自指遥测闸）

**用户令（逐字）**：「那说明你做错了啊，肯定要命中常亮前沿在后面加的，你往中间塞东西了？」+「上下文几乎不涨才是对的」（前序：「你有分析过你的 prompt 么，为何差距这么大」→ 已逐字节定因）。

## 定因（逐字节证据）

- 四份实发 system **前 4,477 字符逐字节相同**，**分叉点 = `[工作区文件 data/activity/<pid>.json]`**（pid 2803414/2810387/2811641/2813373），其后 **757 字符每轮重算** ⇒ 前缀缓存从分叉点起整段失效。
- 该 pid 文件的 `TaskSummary` = 题面原文；另有 `[工作区文件 data/prompt_audit.jsonl]`（09-06 陈旧遥测）随召回进 user 轮。
- 对照：codex 每步只涨 411–444 token（5 轮共 +1,757）；我们 3 步 +3,428。

## 产品改动

| 文件 | 改动 |
|---|---|
| `src/agent/context/SessionInjectionPlanner.cs` | 静态段白名单移出 `[工作区文件]`（含 `[Workspace Files]`），加入 `[技能知识参考]` |
| `src/agent/contextassembler/ContextAssembler.cs` | 工作区自动召回**缺省关** + 自指遥测路径闸（`data/**`、`prompt_audit.jsonl`、`activity/*`）+ 枚举排除 |
| `src/agent.modelqueue/ActionLoop.cs` | `ToolResultCharCap()`（硬顶 `MaxToolResultBytes=8192` 缺省 600 字符） |
| `src/agent.modelqueue/ActionLoopDiscipline.cs` | 纪律 3→5 条（新增「零过渡叙述」「回执按需取全文」） |
| `src/agent.tests/R524PrefixStabilityTests.cs` / `SessionInjectionPlannerTests.cs` | 结构锁；P1 改 |

## v2 三窗真机读数（`eval/rover/r524/`，AOT `7c5b59ef991f11ab…` 15,609,168 B）

| 窗 | M1 常量 | M2 无遥测 | M3 首调用 | M4 步间 | M5 回执 | M6 user 段 | 质量 A1 / A0 / codex |
|---|---|---|---|---|---|---|---|
| w1 | ✅ | ✅ | ✅ 新算 349 | ✅ 504 | ❌ 中位 413 | ❌ | 51/58 · 0/58 · 58/58 |
| w2 | ✅ | ✅ | ✅ 新算 343 | ✅ 495 | ✅ 341 | ❌ | 58/58 · 0/58 · 58/58 |
| w3 | ✅ | ✅ | ✅ | ✅ 473 | ✅ | ❌ | 58/58 · 46/58 · 58/58 |

⇒ **首调用新算 5,372 → 343–349（降 ~15×）**，前缀不再漂移；**M6 未过**（`[技能知识参考]` 4,171 字符仍在 user 轮）。

## 缺口与交接

- **M6 定因**：材料块由 `IndustrialAgentV2.cs:1308` **硬编码**加入 `inlineBlocks`，绕过 `SessionInjectionPlanner` 白名单 ⇒ R525 改为焊进首轮冻结常量前缀（`skillConst`）。
- **A0-off（纪律关）双峰**：0/58 · 0/58 · 46/58 ⇒ 纪律文本在该结构下是工具面对齐的必要条件之一，A0 不构成有效对照臂。
- 铁律 11 前置器 rc=1 ⇒ 本卷读数标「参考（未可验收）」。

## 复现

```bash
bash eval/rover/r524/run_all_r524.sh 0917-r524v2     # 三窗串行
python3 eval/rover/r524/structure_check_r525.py --help   # (R525 版机检; R524 用 prefix_check_r524.py)
```
