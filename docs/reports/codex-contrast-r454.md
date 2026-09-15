# 外部对照报告 · R454 —— codex CLI 为什么做得好 / 本 agent 的问题在哪

- 日期: 2026-09-15 · 轮号 R454 · 证据: `eval/rover/r454/`（含 codex 真实请求体捕获）
- 同输入: `继续下一轮`（两侧同字面）
- 方法: 装 codex-cli 0.154.0 + 自建 OpenAI 兼容/Responses 桩 ⇒ 捕获 codex **真实发出的请求体**；我方面用 R452 捕获读数 + 源码事实双证。全部数字可复跑 `eval/rover/r454/compare_codex_clickagent.py`。

## 1. 结论先行
**codex 强，不在 prompt 小，而在把「能力」放在模型 + 工具面 + 沙箱里；我们的 agent 把能力做在宿主里 —— 远端调用只有 2 条消息、零工具。** 这直接解释了「越做越精细却难兑现 KPI」：我们的精细全花在宿主自建的 plan/absorb/门判/判官上，而模型侧根本没有行动面。

**负控（数据证伪的假设）**：**「codex 好是因为 prompt 更小」不成立** —— codex 单次静态面 **34,542 B**（instructions 16,979 字符 + tools 17,563 B），是我们（≈4,300 B）的 **8.0×**。

## 2. 同输入对照（真实字节）
| 面 | codex-cli 0.154.0 | click-agent（我方） |
|---|---|---|
| 静态面 | instructions **16,979 字符** + tools **17,563 B** = **34,542 B** | system ≈**4,300 B** |
| 工具面 | **9 项**：`exec_command`(1,635 B)、`write_stdin`(819)、`request_user_input`(1,425)、`view_image`(391)、`multi_agent_v1`(**namespace, 10,178 B**)、`get_goal`(297)/`create_goal`(785)/`update_goal`(1,963)、`web_search`(服务端工具) | **0 项**（`ModelQueueRouter.cs:962-966`：请求体只写 `model`+`messages`） |
| 线协议 | **Responses API**（`store=false`、`stream=true`、`include=["reasoning.encrypted_content"]`） | `chat/completions` |
| 缓存 | `prompt_cache_key = <thread_id>` + usage 显式回报 `cached_input_tokens`/`cache_write_input_tokens` | 自建前缀缓存（K2b ≥97%），线协议无缓存字段 |
| 推理 | `reasoning.summary="auto"` | 无 |
| 多轮/多 agent/提问 | **全是显式工具**（`multi_agent_v1`、goal 三件套、`request_user_input`）⇒ 可观测、可关 | 宿主内建机制（plan/absorb/门判/关系判官），模型侧不可见 |
| 批处理/并行 | `parallel_tool_calls=true` | 无工具 ⇒ 不适用 |
| 可编程接口 | `codex exec --json`（JSONL 事件 + usage 真值）、`debug prompt-input`、`app-server`、`--output-schema` | `agenthost --frontend-api`（TCP JSON Lines） |
| 单次实发 input | 3 条（developer 3,015 B + user 559 + user 139） | **2 条**（system + user），`prompt_tokens_est ≈2,467` |

## 3. 为什么 codex 做得好（逐条标 evidence / inference）
1. **能力在模型侧** — evidence：9 个工具 + 34.5 KB 指令面 + `permission_profile`（沙箱/权限随请求下发）。inference：宿主因此能保持「一条循环 + 工具调用 + 沙箱验证」，不必替模型做决策。
2. **大静态面 + 显式前缀缓存键** — evidence：`prompt_cache_key`、usage 里的 `cached_input_tokens`。inference：**大 prompt ≠ 贵**，34.5 KB 稳定前缀被缓存后按增量计费。我方 4.3 KB + K2b ≥97% 同路 ⇒ **这一条我们已经做对**。
3. **一致性来自可验证的动作面** — evidence：`exec_command`/`write_stdin` + 沙箱权限；跑起来看结果。inference：我们的质量闭环靠**自建器具**（预注册/判据/外部真值/登记表）——这是 codex 没有的**真资产**，但也是「精细却没跑测」的高发区。
4. **codex 不做本地小模型判真假、不设 Skip** — evidence：工具面/usage/参数面没有任何本地模型路径。inference：与我们 R449/R452 实测一致（真实流量 S 票 **14/14 全被机械认可族守卫否决**、可跳面 **0**）⇒ 该路线在真实分布上收益 ≈0。
5. **多 agent / 目标 / 提问都是显式工具** — evidence：`multi_agent_v1`(namespace)、`get/create/update_goal`、`request_user_input`。inference：宿主不需要自造隐藏机制，能力差异可直接对照。

## 4. 本 agent 的问题（按代价排序）
- **P1 远端面没有工具面**（`ModelQueueRouter.cs:962-966`）：模型只能产出文本，任何「让 agent 自己干活」的责任都落到宿主 ⇒ 宿主复杂度不断膨胀。**这是与 codex 的根本差距。**
- **P2 自建判官/门在真实分布不可用**：真实流量 r1 判官 S 票 14/14 被守卫否决、生产配置 0 次 r1 调用 ⇒ 继续投在这条线上 = 无用功。
- **P3 器具链自身缺「执行数 > 0」断言**：本轮抓到自己的形式门禁过滤器拼错（`FormalCheck` 不存在）而 `dotnet test` 仍 rc=0 ⇒ **假绿**。已修（真名 `VerificationFormTests`，9/9 Passed）。
- **P4 质量裁决在本机不可做**：桩应答非真回复；质量对照需真模型或部署端数据。
- **P5 absorb/参数槽通道只能台账，无法质量裁决**（R453 结论）。

## 5. 避免无用功 —— 建议（可执行）
| 动作 | 依据 |
|---|---|
| **停**：门判/判官族扩面、判官输入友好化 | P2 + codex 无此机制 |
| **停/缓**：自建 absorb 参数槽扩面 | R453：只能说清量级（13.7%），无法质量裁决 |
| **转**：把「同题双跑」做成常规回归 —— `codex exec --json`（input/cached/output/reasoning token 真值）vs `agenthost`，同模型/同模板/同截断 | 用户钦定「对照相同输入的返回」⇒ 这是直接量尺 |
| **保**：器具链（预注册 + 外部真值 + 登记表）不动 | P3 修好后仍是我们唯一的护城河 |
| **若补 P1**：给远端请求加最小工具面（read/write/exec 三件套）+ 沙箱权限声明 ⇒ 结构级改动，须独立预注册轮 + AOT 复发布 + 质量 A/B | 唯一与 codex 实质对齐的路径 |

## 6. 诚实边界
- codex 侧 = **1 次捕获**（1 个输入、默认配置、无 AGENTS.md）；换 `-c` 配置会变（工具可关）。
- 我方侧**未新抓包**：`MemAvailable 2477 MB < 2650 MB` 内存闸禁起 llama-server ⇒ 用 R452 已捕获读数 + 源码事实双证；「零工具」是**源码事实**而非推断。
- 只比**请求面/接口面**，**不比回答质量**（桩输出非模型输出）。codex 事件流含 1 条 `Model metadata for gpt-5-codex not found`（我用桩 provider，无元数据），不影响请求面。
- codex 的 `web_search`/`multi_agent_v1` 是**服务端/命名空间**工具：真机走 OpenAI 端，本机桩只捕获其 schema。
