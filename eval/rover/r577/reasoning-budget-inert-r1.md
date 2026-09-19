# R577-c · `--reasoning-budget` 对 r1 无效（机制取证）

日期：2026-09-19 · 器具：`eval/rover/r462/bench_r462_w.py`（sha256[:12] `8a8b895d27dd`）· 语料 `/tmp/r462_corpus.json`（`cd075177be5b`，28 条产品实发 prompt）

## 目的问题
r1（`DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M`）在判别位恒判 S（假跳 14/14）。假设：把思维链关掉即可恢复。可用的关法有三条：
1. 服务端 flag `--reasoning-budget 0`（env `LLAMA_ARG_THINK_BUDGET`，README:235「0 for immediate end」）
2. 自定义模板 `--chat-template-file`
3. prompt 侧预填空思考块（R1 模板惯例：`<｜Assistant｜>` 后接 ` thinking\n\n<｜end▁of▁thinking｜>\n\n`）

## 取证 A：模板能力（决定 flag 是否能生效）
`/tmp/r577_tpl_probe.py` 读 GGUF KV `tokenizer.chat_template`：

| 模型 | 模板长度 | `enable_thinking` | `reasoning_effort` | `reasoning_content` | 模板是否声明 thinking 能力 |
|---|---|---|---|---|---|
| r1-distill-qwen-1.5b-q4km | 2,081 | **0** | **0** | **0** | **否** |
| qwen2.5-1.5b-instruct-q4km | 2,509 | 0 | 0 | 0 | 否（纯 instruct，无思考） |
| LFM2.5-VL-3B-Q4_K_M | 5,436 | 0 | 0 | 1（`thinking` 13） | 是（但默认不思考，实测裸 `S`） |

`tools/server/server-context.cpp:1463-1465`：`enable_thinking = params_base.enable_reasoning != 0 && template_supports_thinking`
⇒ r1 模板不含思考开关 ⇒ **`template_supports_thinking=false` ⇒ flag 对该模型结构性失效**。

## 取证 B：实测（单变量 = 只加一个 env，器具 sha 不变）
`LLAMA_ARG_THINK_BUDGET=0 python3 eval/rover/r462/bench_r462_w.py --model r1… --tag r577-r1-nothink`（port 48792）

| 项 | gen tokens | wall |
|---|---|---|
| 1 | 146 | 22.81 s |
| 2 | 58 | 15.96 s |
| 3 | 120 | 18.84 s |
| 4 | 70 | 14.06 s |

基线（同器具同权重，`arm-r1-requal.json`）= **157.8 token/次**。本臂均值 ≈ 98（4 项样本，含波动）⇒ **思维链仍在生成**，仅被截短了尾部（budget 语义在无能力模板下不触发提前收尾）。
臂于 4/28 中止（`process.kill`）——判定为**非独立条件**，不作为候选臂读数。

## 结论
- 「关思考」若要走服务端 flag，**对 r1 不可行**；可行路径只剩 2（自定义模板）或 3（prompt 预填）。
- 路径 3 的成本 = 需要 prompt 变体语料（现器具语料路径硬编码 `/tmp/r462_corpus.json`，无 `--corpus` 参数）⇒ 属语料面改动，需单独登记；且即使成功，省下的是「换模型」而非「更快」（每轮耗时由 452–503 token 预填主导，r1 关思考后 ≈ LFM2.5-3B 的 15.8 s/次）。
- 判别位首选仍是**实测已达标档**：`LFM2.5-VL-3B-Q4_K_M`（acc 1.0 / 假跳 0/14 / gen 2 token/次 / 15.8 s/次，`arm-lfm3b-requal.json`）。
