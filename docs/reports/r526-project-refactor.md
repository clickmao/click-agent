# R526 (2026-09-17) — 项目级「完全重构」

**靶点（用户令，逐字）**：「完全重构当前项目，如果不懂怎么重构，重构是什么的意思入网上搜」。
本文件同时回答「重构是什么」与「这次到底改了什么、凭什么说没改坏」。

## 1. 重构的定义与判据（先定义，再执行）

「重构 (refactoring)」= **在不改变外部可见行为的前提下改善代码内部结构**（Fowler）。它由两条判据同时定义，缺一不算重构：

| 判据 | R526 的守门方式 | 读数 |
|---|---|---|
| **外部行为不变** | 全量测试 1755 例 + `agent.sln` 构建 | 1755/1755 绿；0 错误（每阶段各跑一次） |
| **目标结构不变式成立** | `RefactorStructureTests`（I1/I2/I3a/I3b）+ 独立机检 `tools/refactor/invariant_check.py` + 负控 | 4 条不变式全 0 违规；负控 4 类注入全红 |

大型重构 = **受控的机械变换序列**，每步只做一类变换、每步后由编译器与测试守门；不做「一次性大改 + 事后修复」。

## 2. 变换流水（每步都有构建/测试读数）

| 阶段 | 变换 | 器具 | 守门读数 |
|---|---|---|---|
| A | **类型单一化**：176 个多类型文件 → 每个顶层类型独占一文件（575 个类型外移；`file` 作用域类型按语义跳过） | `tools/refactor/reftool extract`（Roslyn 语法树，非文本正则） | 构建 0 错误；测试 3 红（源码扫描型，见 §5） |
| B1 | **命名空间归一**：`agent.Recall*` → 小写（61 文件）；测试命名空间 `agentframework.tests` → `agent.tests`（88 改写 + 6 补）；头部区 using 去重 | `pipeline/02` | 构建 0 错误；CS0105 归零 |
| B2 | **巨类拆分**：`IndustrialAgentV2` 3204 行 → 主 2263 + `Commands` 441 + `Plan` 215 + `Context` 372（4 个 partial；字段/嵌套类型留主文件） | `tools/refactor/reftool split` | 构建 0 错误 |
| C1 | **构建配置集中化**：`src/Directory.Build.props`（TFM/Nullable/ImplicitUsings/LangVersion 默认值）+ 25 个 csproj 去重 | `pipeline/04` | 构建 0 错误（例外项目自持覆盖） |
| C2 | **钉死引用同步**：登记表 `covers` 36 行改指新文件；4 处源码扫描型测试改目录级/片段级 | `pipeline/06,07` | 全量测试 1755/1755 绿 |
| D | **容器文件改名**：32 个「文件名 ≠ 类型名」文件改名为 `<类型名>.cs`；20 个缺命名空间文件补齐；`CredentialEncryption.cs` 归位 `agent` | `pipeline/05` + 手工收口 | 构建 0 错误；I2/I3 归零 |

## 3. 前后对照

| 指标 | 重构前 (R525 `bad0c42`) | 重构后 (R526) |
|---|---|---|
| `src` 下 `.cs` 文件数 | 475 | **1054** |
| `src` 总行数 | 93,828 | 97,045 |
| 含 >1 顶层类型的文件 | **176** | **0** |
| 文件名 ≠ 类型名的文件 | 33 | **0** |
| 无命名空间声明的文件 | 20 | **0**（`Program.cs` 顶层语句除外，已登记豁免） |
| 目录内混用命名空间的目录 | 4 | **0**（`agent.core` 两处遗产已逐条登记豁免） |
| 单文件最大类 | `IndustrialAgentV2` 3204 行 | 主文件 2263 行（拆 4 partial） |
| 构建配置重复 | 25 个 csproj 各自重复 4 个属性 | `src/Directory.Build.props` 统一，例外项目自持 |
| 测试 | 1750 例 | **1755 例**（+5 结构不变式守卫） |
| 编译告警 | 24（同类） | 24（CS86xx nullable / CS0169·CS0649·CS0219 未用；**CS0102/CS0103/CS0105/CS0246 类为 0**） |

## 4. 结构与外部行为的双重验证

- **构建**：`agent.sln` 每阶段 0 错误（Debug 全量 rebuild）。
- **测试**：1755/1755 绿（含 R525 提示词结构锁 M1/M2/M5/M6/S1–S5、R524 前缀稳定、登记表形式门禁 R2c/R2e）。
  期间出现过 1 次 `FrontendAskSameConnTests.请求处理中触发ask_同连接答复可被读取并续跑` 失败：**隔离复跑 2 次全过 + 全量复跑 1755/1755 过**
  ⇒ 记为偶发（该例走真实连接时序，与本次纯结构变换无因果）；失败样本与终态绿样本**分别留档**
  （`eval/rover/r526/evidence/tests-full-r526-flaky1.txt` / `tests-full-r526.txt`），未用「复跑通过」覆盖掉失败记录。
- **结构机检**：1054 个 `.cs`，I1/I2/I3a/I3b 全 0 违规；负控面板（一个文件塞两类型 / 文件名≠类型名 / 缺命名空间 / 同目录混命名空间）**全部判红** ⇒ 判据非恒绿。
- **AOT 发布**：见 §7（发布形态铁律：一切功能以 AOT 可用为验收）。

## 5. 重构暴露的真实缺陷（顺手修掉的，不是凭空的）

1. `agent.Recall*` 与全仓小写命名空间约定相反（61 文件）；
2. 测试项目内两套命名空间并存（101 vs 88）且 6 个文件根本没有命名空间；
3. `agent.io` 17 个文件、`agent.vectormemory` 2 个、`agent.skills` 1 个文件缺命名空间（掉在全局命名空间）；
4. `src/agent/CredentialEncryption.cs` 声明 `agent.userinteraction`，而它住在 `src/agent/`（与 19 个兄弟文件不一致）；
5. `agent.core/{userinteraction,subagent}` 20 个文件沿用 `agent.userinteraction` / `agent.subagent`
   —— 同一命名空间横跨两个程序集（**未修，见 §6 候选**）；
6. 25 个 csproj 重复同一批构建属性（无 `Directory.Build.props`）。

## 6. 诚实边界

- **`agent.core` 命名空间遗产未收敛**：20 个文件（`agent.core/userinteraction` 16 + `agent.core/subagent` 4）继续用
  `agent.userinteraction`/`agent.subagent`。改正需要跨程序集改名 + 逐类型引用重写（两侧命名空间共享，改名会让引用二义化），
  属**语义敏感变换**，不在本轮机械变换范围内；已用**逐条豁免**锁住（新违规不豁免），列为下轮候选。
- **`OnProcessAsync` 仍 1,662 行**：巨类拆分只做「成员级」机械切分；单个方法内部的逻辑抽取需要语义分析（等价于重写），
  不在机械重构范围。下一个可机械处理的靶点见候选。
- **`src/agent.modelqueue/ModelQueueRouter.cs`（1530 行）/ `ContextAssembler.cs`（1513 行）**未拆 partial —— 本轮只拆了
  最大的那个类；这两个文件现已是单类型，符合不变式，但方法体量仍大。
- **行数不降反增**（93,828 → 97,045，+3.4%）：单类型单文件必然带来「文件头 usings + namespace」重复；
  这是空间换结构清晰，不构成性能/产物体积回归（AOT 产物 sha 与体积见 §7）。
- **未做**：方法级逻辑重构（Extract Method/Class 的语义版）、跨程序集命名空间收敛、`Directory.Packages.props`（中央包版本管理）。
- 「完全重构」在工程上**永远不是一次动作**：本轮交付的是**结构层的一次完整闭合**（不变式全部成立 + 判据可执行 + 负控在位），
  语义层的收敛属于后续轮次。

## 7. AOT 与产物

- 发布命令（**禁加 `/p:PublishAot=true`** — 发布铁律）：`dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_r526`
- 产物：`/tmp/pub_r526/agenthost` — **15,617,360 B**，sha256 `6b565aa044b722cc54ede898…`（native ELF / stripped；
  与 R525 产物同量级 ⇒ 结构重构未引入体积回归）。证据：`eval/rover/r526/evidence/aot-artifact.txt`。
- 冒烟（真机执行）：`printf '/status\n/exit\n' | /tmp/pub_r526/agenthost` → **rc=0**；宿主启动、prompt 构建完成（`~4952 tokens`）、
  E2E 因**未配置模型凭据**而诚实失败（未伪造成功）。证据：`eval/rover/r526/evidence/aot-smoke.txt`。

## 8. 下轮候选

1. `agent.core` 两处命名空间遗产收敛（跨程序集改名 + 引用重写，需 Roslyn 语义层）。
2. `OnProcessAsync` 1,662 行的方法级抽取（语义重写，需等价性夹具）。
3. `ModelQueueRouter` / `ContextAssembler` 的 partial 拆分（机械，按成员边界）。
4. `Directory.Packages.props` 中央包版本管理（25 csproj 的 PackageReference 版本收敛）。
5. 结构不变式接入**新增文件**前置闸（当前为测试期机检；下一步可在提交前跑 `invariant_check.py`）。
