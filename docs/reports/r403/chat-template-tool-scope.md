# R403 裁定 — chat template 全量（Jinja 子集扩展 + 工具调用模板）

**日期**: 2026-09-14 · **轮**: R403-scope · **状态**: 关闭（两条子项各自结清 + 待触发能力登记）
**证据**: `eval/rover/r403/tool-template-behavior.json`（机器可读）+ `eval/rover/r403/probe_tool_template.py`（可复跑，一条命令重跑得同结论）

---

## 1. 待判问题（backlog R403 原文）

> **待判**：工具调用模板是否改口径为「验证 llama.cpp tool 模板行为」

本轮只判这一件事，不动其它状态（避免把两件事并成一步 —— 与 `docs/reports/r411v/registry-liveness.md` §6.4 预留一致）。

## 2. 前提（R408/R409 已钉死，本轮仅复核引用）

- R408 §3-Q5：分词与聊天模板交给 llama.cpp（`--jinja` + 模型自带模板）⇒ **自研 Jinja 子集扩展的对象已退役**；
- R409：模板由服务端 `/apply-template` 按模型元数据渲染（与归档 `eval/rover/tokref/r1_chat_template.jinja` 3/3 字节一致）⇒ 调用方物理上无法手拼。
  ⇒ 剩下唯一待判的是「工具调用」这一半。

## 3. 方法（两臂 + 判别力负控，一条命令可复跑）

```
python3 eval/rover/r403/probe_tool_template.py      # R403_PROBE_EXIT=0 arms_ok=2/2
```

| 臂 | 模板来源 | 目的 |
|---|---|---|
| `default_gguf_template` | GGUF 元数据自带模板（`--jinja`） | 被测对象：现役模型的工具调用模板行为 |
| `control_synthetic_tools_template` | 合成最小模板（`--chat-template-file`，258 B，**全 ASCII**） | **负控**：探针必须能把「支持渲染」与「不支持」判成不同结果 |

每臂读数：`/props.chat_template_caps` ＋ 模板源统计 ＋ `/apply-template` ±tools 产物 md5 ＋
`/v1/chat/completions` ±tools 的 `prompt_tokens`（同 messages、`max_tokens=1`）。
共同运行条件：`-c 512 -t 1 -np 1 --jinja`、**f32 KV**、`--flash-attn off`（档位显式钉死，R407 纪律）。

## 4. 读数（实测，非推断）

| 臂 | caps.supports_tools | caps.supports_tool_calls | 模板源 `tools` 变量数 | apply-template ±tools | completions prompt_tokens ±tools | Δ | HTTP |
|---|---|---|---|---|---|---|---|
| default | **false** | **false** | **0**（另：`tool_calls` 1 处、`== 'tool'` 1 处 ⇒ 只能回显既有工具消息，无可用工具定义位） | **逐字节相同** `b89299b3a8f11401feaf35c459002e32`（24 B / 24 B） | **4 / 4** | **0** | 200 |
| control（负控） | **true** | false | 2 | **不同**（29 B vs 62 B） | **7 / 18** | **+11** | 200 |

- 模板源统计（default）：`chars=2081 / utf8_bytes=2237`，`tools`=0、`definitions`=0、`tool_calls`=1、`== 'tool'`=1。
- 产品侧消费方：`grep -rn -E 'tool_choice|ToolCall|tool_calls|"tools"' src/ --include=*.cs` ⇒ **0 命中**（无任何发出 tools 的调用点）。

## 5. 判读（含替代解释的排除）

1. **负控先过关**：同一探针在支持渲染的模板上把两态分开（md5 不同、Δ=+11 token），且 `caps.supports_tools` 随模板翻转
   ⇒ 该字段是**模板派生**而非常量，探针有判别力 ⇒ default 臂的「完全相同」是真读数，不是探针盲区。
2. **排除了「端点不支持 tools」的替代解释**：`/apply-template` 在 control 臂**读到了** tools 并改变了渲染产物
   ⇒ 端点确实转发 tools，default 臂的相同输出来自**模板**（引擎找不到可渲染工具的位点）。
3. **静默丢弃的确证形态**：default 臂带 tools 请求 **HTTP 200 + 无报错 + prompt 逐字节不变**（token 数 4→4）
   ⇒ 「上游受理」在这里**不是**「上游渲染」；只凭 200/无异常判「支持工具调用」会把静默丢弃当成功。
4. ⇒ **「改口径为验证工具调用模板」在本机引擎 + 现役模型上无对象可验**：不是「没测到」，是**引擎自报不支持 ∧ 模板零工具定义位 ∧ 产品零消费方**三方一致。

## 6. 裁定

**R403 关闭**，两条子项分别结清：

1. **自研 Jinja 子集扩展** — 对象随 R408 退役（R409 实证渲染由引擎按模型元数据完成，调用方无法手拼）；
2. **工具调用模板** — 无对象（§5）；不改口径另立验证项，因为当前无任何一方提供该面。

「工具调用」转为**待触发能力**，准入判据（三条**全绿**才开工，缺一即视为未到期）：

- **(a) 能力位**：目标模型 `/props.chat_template_caps.supports_tools == true`；
- **(b) 渲染生效**：同 messages ±tools 的 `prompt_tokens` 有差（或 `/apply-template` 产物 md5 不同）——**不得只看 HTTP 200**；
- **(c) 消费方存在**：产品侧存在发出 tools 的调用点（grep 计数 ≥1）。

## 7. 诚实边界

- 仅测**现役模型** `r1-distill-qwen-1.5b-q4km` + 本机 build `b1-4df29be`；换模型/换 build 须重跑脚本（已参数化 `R403_MODEL` / `AGENTFRAMEWORK_LLAMA_BIN`）。
- 负控模板是**合成最小模板**，只证「探针有判别力」，**不证**任何真实模型支持工具调用，也**不证**它的渲染质量。
- **未测**：若模板真的支持 tools，llama.cpp 的工具调用**出参解析**（`tool_calls` → OpenAI 格式）是否正确 —— 需要真实支持模板的模型，属准入判据 (a) 之后的独立课题。
- 单机单 build 的单次读数（两臂各一次；重跑一致属预期，未做多次重复）。

## 8. 运行记录（含本轮两次事故，如实入档）

- **清场前置**：测量前按 pid 清理 6 个 R412/R413 遗留长驻 server（pid 230833/230849/232136/232152/233614/233632，RSS 合计 ≈3.5 GB，无活跃 runner、无 established 连接）⇒ `MemAvailable` 1.14 GB → **2.99 GB**（本机共 3.66 GB）。
- **自匹配事故（第二次同族）**：`pgrep -f "[4]1999"` 仍把**我自己**杀掉（退出码 −15）——括号技巧只保护**模式字面量**，不保护同一命令行里**别处**出现的裸目标串（我的 `curl ... :41999/props` 含端口号）。同族再现：`ps | grep "[l]lama-server"` 匹配到自身，因为同一命令行的 `echo "no llama-server running"` 兜底文案含目标串。
  ⇒ 正确姿势：让被测进程**自己落 pid**，或在**同一进程内** Popen 并 `killpg` 收尾（本脚本用后者，故无孤儿）。
- **泄漏检查**：脚本收尾 `killpg(SIGTERM→SIGKILL)`；结束后 `MemAvailable` 2.71 GB，无 llama-server 存活。
