# R447 证据：判官解码侧约束（单字母 GBNF）的等价性与收益 —— **负结论**

- 轮次：R447（承 R446）｜形态：真机探针（**零产品代码改动**）｜预注册：`eval/rover/r447/prereg.json`（先落盘，sha256 记入结果）
- 计划：`docs/plans/v0.67.0-r447-judge-decode-constraint.md`｜机检：`eval/rover/r447/r447_analyze.py` → `verdict-r447.json`
- 真机：`/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server` + `/tmp/models/r1-distill-qwen-1.5b-q4km.gguf`（argv 直取自 `/proc/<pid>/cmdline`：`-c 4608 -t 1 -np 1 --cache-type-k f32 --cache-type-v f32 --flash-attn off --jinja`）

## 1. 因果链（每一步都有前轮读数背书）

1. R443/R444 把本地 r1 真值钉死在 llama-server 的 `tokens_evaluated / tokens_predicted`（`gen`），M20 BRJ 全本地真值 **7841 tok**（其中判官 4738）。
2. R446 机制结论：判官本地成本里 **生成 1974 / 预填充 2764**，生成占 ~42%，且判官 `maxTokens` 被舍入到 **512**（`max(256,512)`），模型自发思考 92–194 tok 才吐字母。
3. 推论（本轮靶）：若能**解码侧强制单字母**，判官生成可降到 ~2 tok ⇒ 省 ~1.9k tok/20 轮。这是「不必要的远端 API 请求之外」的第二条降本通道。
4. 但生成侧承载思考 ⇒ 必须**先证等价**再谈启用（R446 曾因 prompt 收缩不等价而封存开关）。故本轮＝真机等价性消融。

## 2. 本轮产出（文件 / 命令 / 读数）

| 物 | 说明 |
|---|---|
| `eval/rover/r447/r447_corpus.py` → `corpus.json` | 真语料构建器（v2）。prompt **源码派生**（`BuildJudgePromptVerbose` 字面量重解，禁手打）；**忠实性闸：与 `eval/rover/r435/judge-prompt-golden-v2.jsonl` 逐字 9/9 相同** |
| `eval/rover/r447/r447_probe.py` → `probe-r447.json` | 真机 4 臂（J0/J1/J2 + NC1）+ 形态自证（argv/props/逐请求 body 落盘） |
| `eval/rover/r447/r447_probe_nc1b.py` → `probe-r447-nc1b.json` | posthoc：**真错配 prev** 负控（修 C4a 的判定项设计缺陷） |
| `eval/rover/r447/r447_analyze.py` → `verdict-r447.json` | C1–C6 机检 + `checks_posthoc`（CH1–CH3） |
| 命令 | `python3 eval/rover/r447/r447_probe.py`（~11 min）→ `python3 eval/rover/r447/r447_probe_nc1b.py`（~3 min）→ `python3 eval/rover/r447/r447_analyze.py` |

### 语料（18 对真实 `(msg, prev)`）

- 12 对：**遥测真值对**。来源 = `eval/rover/r4*/run-*/data/telemetry/host.jsonl` 的 `correction_judge` 行（本地实答）；`msg` 由 run 名映射到同轮 `grid/task-*.json` 的 `turns` 解出；`prev` 由 **`prompt_len` 恒等式**判定（`plen = 262 + len(prev) + len(msg)`，候选 = 桩应答 15 / 跳过应答 21）。
- 6 对：`judge-prompt-golden-v2.jsonl` 的 syn 案例（`prev` 为**真实上一轮回复** 26 字符）。
- **v1 被推翻（器具自纠，留痕）**：v1 从 `calls-*.jsonl` 的 `messages` 取「最后 user + 前一条 assistant」——但归档里 user 消息带 `[本轮参考上下文]` 内联块，而判官实收 `question` 是**裸消息**（遥测 `msg_head` 无块）⇒ v1 语料不忠实，改用 v2（拒绝理由写进 `corpus.json.rejected_sources`）。

## 3. 读数（`verdict-r447.json`）

| 判据 | 结果 | 读数 |
|---|---|---|
| C1 非空心 | **PASS** | 可解析率 J0 0.944 / J1 1.0 / NC1 1.0；J0 字母 {A,C,N} 三态齐 |
| C2 生成降幅 | **PASS** | `gen` J0 均值 **178.6**（中位 169，max 512，Σ3215）→ J1 均值 **2.0**（恒 2，Σ36）；比值 **0.0112**；墙钟 15.75s → 5.6s |
| **C3 等价** | **FAIL** | `agree(J1,J0) = 0.4444`（18 条）。混淆矩阵：`A→A 8 / C→A 2 / N→A 7 / 截断→A 1` ⇒ **J1 = 18/18 恒 `A`** |
| C4a 负控(错配 prev) | **FAIL（判定项设计缺陷）** | `agree(NC1,J0)=0.875`，且 **8 条里只有 2 条真错配**（prev 候选只有 2 个常量，相邻对常同值）⇒ 该判据在本语料上不可测 |
| C4b 负控(恒 N 平凡结算器) | **PASS** | `agree(NC2,J0)=0.3889` < 0.90（= J0 的 N 占比 0.389）⇒ 指标有判别力 |
| C4c 归档第三通道 | **PASS** | J0 与归档产物字母 **12/12 逐条相同** ⇒ 探针忠实复现产品判决 |
| C5 记账自洽 | **PASS（部分）** | 全 54 次调用 `cache_n ≡ 0`；逐样本 `prompt_n` 跨臂相等（214/212/…同 prompt ⇒ 同预填充）。**未测**：`tokens_evaluated == prompt_n + cache_n` 恒等式（本轮只落了 `tokens_evaluated`，未落 `timings.prompt_n`） |
| C6 形态自证 | **PASS** | argv 含 `-np 1 / --cache-type-{k,v} f32 / --flash-attn off / -c 4608 / --jinja`；逐请求 body 与预注册解码档全字段相同；`props.temperature=0.8` 为**服务端默认值**（不生效：请求显式 `samplers=["temperature"], temperature=0.0`），已注明防误读 |

**J2（只砍预算不做约束，n_predict=8）**：18/18 `thinking_truncated`，内容长度恒 19–20 字符（`<think>` + 8 tok 思考碎片）⇒ 「只砍预算」必然解析失败（产品会 fallback 远端，反而更贵）。这条独立钉死了「必须约束解码」这个前提。

### 事后判据 `checks_posthoc`

- **CH1 真错配 prev（pass）**：把 orig prev 全换成「另一个真值 prev」后 `agree(NC1b,J0) = 0.5`（8/8 真错配）⇒ **基线判决确实依赖 prev**（器具非空心），参照系 = C4c 的 1.0 自洽率 + R446 的「同输入⇒同字母」。
- **CH2 语法臂 vs 产品真值（pass）**：`agree(J1, 归档) = 0.5`（J1 恒 A，恰好等于真值里 A 的占比）⇒ 独立复现 C3 红。
- **CH3 登记型发现**：J0 有 **1/18 触 512 上限**未吐字母（`从头再说。`，prev=21 字符跳过应答）⇒ 现网判官预算 512 并非总是足够：该情形产品会先白付 512 本地 tok 再 fallback 远端。

## 4. 结论与决策

- 判决：**存在红项（C3、C4a）⇒ 负结论归档，解码侧单字母约束不得启用**。
- 机制：约束单字母等于**取消思考**；该模型的判决**不是**首 token 先验——强制首 token 后它恒定输出 `A`（18/18），相对产品真值只有 0.5 一致率。**思考是判决的承重结构，不可用生成预算约束换。**
- 收益上限（仅作反事实记录，不计入 KPI）：若等价成立，M20 判官本地生成 1974 → 26（省 1948 tok = 全本地真值 7841 的 **24.8%**）。该路径已关闭。
- 零产品代码改动 ⇒ **本轮无 AOT/测试对象**（不触发「改链代码必 AOT 重发布」铁律）；无链跑 ⇒ **不写 `eval/capability/kpi.jsonl`**（避免污染 KPI 台账）。

## 5. 诚实边界

1. 单模型档（`r1-distill-1.5b-q4km`）+ 单容器（`-c 4608`）；未测其它档位/量化。
2. 语料 `msg` 全为短消息（≤18 字符）；长消息 / 长 prev（>120 截断）未覆盖。
3. `prev` 面多样性有限（真值只有 3 种：桩应答、跳过应答、1 条真实回复）⇒ 等价性证据在 **msg 面强、prev 面弱**；CH1 只证明「prev 有效」，未证明「prev 多样性足够」。
4. C5 恒等式一项未测（见上）；C4a 为判定项设计缺陷，其语义已由 posthoc CH1 承接（**不得宣称预注册全绿**）。
5. 未做远端 A/B（等价性未过 ⇒ 无必要），也未测真实 API 计费/时延。
6. 门通道（`local_turn_gate`，同构：7 调用 / 生成 913 tok / 均值 ~130）**本轮未测**。

## 6. 下轮候选

1. **R448：判官 prompt 侧「限长思考」消融**（不取消思考，改为「思考不超过 2 句，随后必须另起一行只写字母」+ `n_predict 128`）：靶 = ①生成 178→≤64 ②与归档真值一致率 ≥0.9 ③消掉 CH3 的 1/18 截断。← **首选**（保留思考，风险最低，且直接吃掉 CH3 缺陷）。
2. **R448：门通道同构消融**（`local_turn_gate` 生成 ~130 tok/调用 ×7）：先做只读机制复现，再与判官同臂。
3. **R449：`-c 4608` 之外的预算档**（256/384）对 CH3 截断率的影响（判官 + 门联测）。
4. **R449：把「prev 候选数 ≥3 + 真错配断言」写进语料构建器的机械闸**（防 C4a 同类判定项缺陷复发）。
