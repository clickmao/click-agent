# R448 证据：判官 prompt 侧「限长思考」消融 —— **负结论**

- 轮次：R448（承 R446 机制 + R447 负结论）｜形态：真机探针（**零产品代码改动** ⇒ 无 AOT/测试对象）
- 预注册：`eval/rover/r448/prereg.json`（先落盘；`probe-r448.json.prereg.sha256` 供核对先后 = `8979b3f8…`）
- 计划：`docs/plans/v0.68.0-r448-judge-think-length-cap.md`｜机检：`r448_analyze.py` → `verdict-r448.json`
- 真机：`/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server` + `/tmp/models/r1-distill-qwen-1.5b-q4km.gguf`
  argv（直取 `/proc/<pid>/cmdline`）：`-c 4608 -t 1 -np 1 --cache-type-k f32 --cache-type-v f32 --flash-attn off --jinja`

## 1. 因果链

1. R446 机制：M20 判官本地成本 = 预填充 2764 + **生成 1974**（全本地真值 7841，含本地口径降幅 33.32%）。
2. R447 已判死**解码侧**强制单字母（取消思考 ⇒ 18/18 恒 `A`、agree 0.4444）⇒ **思考是判决的承重结构**。
3. 本轮唯一未测形态：**保留思考、限制其长度**（prompt 插入限长子句 + `n_predict` 收敛）。
4. 启用前提 = 等价（与产品原样 prompt 逐样本判决一致率 ≥0.90）。本轮即该前提的真机检验。

## 2. 臂与语料

| 臂 | prompt | n_predict | 请求体自证 |
|---|---|---|---|
| J0 | 产品原样（源码派生重建） | 512 | `n_predict=512, temperature=0.0, samplers=["temperature"], cache_prompt=false`，渲染后 311 tok |
| T2 | 产品 + 限长子句 | 512 | 同上，prompt 339 tok |
| T1 | 产品 + 限长子句 | 128 | `n_predict=128`，prompt 339 tok |
| NC1t | T1 同配置 + 真错配 prev | 128 | 8 对，真错配 8/8（G3 机检） |

- 限长子句（唯一插入文本）：`思考最多 2 句 (不超过 40 字), 不要展开推理。`；插入锚点 = `CorrectionDetector.cs:BuildJudgePromptVerbose` 的「先思考…」字面量（源码派生）。
- 语料 = 18 对真实 `(msg, prev)`（12 遥测 local 真值对 + 6 golden 真值对），快照 `input-corpus.json`。
- **机械闸**：G1 独立重建 18/18 与快照逐字节相同｜G1b 忠实性 9/9 产品实发原文｜G2 prev 多样性下界（distinct=3、>25 字符 1 条，**只钉下界不宣称强**）｜**G3 负控真错配 8/8**。

## 3. 读数（`verdict-r448.json`）

| 判据 | 结果 | 读数 |
|---|---|---|
| C1 非空心 | **FAIL** | 可解析率 J0 0.9444 / T2 1.0 / **T1 0.3333**（T1 字母种类 3，非恒字母但多数不可解析） |
| C2 生成降幅 | **FAIL** | gen 均值 J0 **178.6**（median 169, max 512, Σ3215）→ T1 **119.7**（median **128** = 触顶）；比值 **0.6702**（阈值 ≤0.36） |
| C3 prompt 单独效应 | **FAIL** | T2 gen 均值 **138.5**（median 138.5, max 211, 0/18 截断）：比值 **0.7755**（>0.75）**且** agree(T2,J0) = **0.4444**（<0.90） |
| **C4 等价** | **FAIL** | agree(T1,J0) = **0.1667**；agree(T1, 归档 12 条) = **0.1667**；分歧 14/18 |
| C5 截断闭合 | **FAIL** | T1 `thinking_truncated` **11**（61.1%）+ `empty_conclusion` 1；J0 = 1（复现 R447 CH3） |
| C6 负控 | **PASS** | 真错配 8/8 且 agree(NC1t,T1) = **0.0** ≤0.85 ⇒ 器具非空心 |
| C7 记账/形态 | **FAIL（判定项设计缺陷）** | `cache_n≡0` 62/62 ✔；恒等式 `tokens_evaluated == timings.prompt_n + cache_n` **62/62** ✔（**闭合 R447 C5 未测债**）；argv ✔；**「逐样本 prompt_n 跨臂相等」0/18 ✘（T 臂 prompt 比 J0 长 28 字符 ⇒ 按定义不可能成立）** |

**决策**：6 红 ⇒ 负结论归档，限长思考不得启用。

## 4. 事后判据 `checks_posthoc`

- **CH1 vs R447 解码约束**：R447 J1 = gen 恒 2、字母恒 A；本轮 T1 保留思考（gen 均值 119.7、种类 3）⇒ 两条路**失效方式不同、结论一致**（都不等价）。
- **CH2 归档第三通道**：J0 与归档产品字母 **12/12** 逐条相同（R447 同通道亦 12/12）⇒ 探针忠实复现产品判决。
- **CH3 分歧清单**：14/18 条 T1≠J0（如 `换个讲法。` J0=A → T1=N）。
- **CH4 反事实上限**（不计入 KPI）：按 0.67 折算判官生成 ⇒ M20「含本地真值」口径 33.32% → **34.38%（+1.06 pt）**；收益/风险不成比例。
- **CH5 T1 内容长度**：min 140 / median 220 / max 230（截断样本仍在思考区内 ⇒ 不是「短思考」而是「被砍断的思考」）。
- **CH6 记账口径修正**（C7 缺陷承接）：同 prompt 臂 **T2 vs T1 逐样本 prompt_n 相等 18/18**；`cache_n` 全零、恒等式全绿、argv 全绿。
- **CH7 跨轮确定性**：本轮 J0 `Σgen = 3215`，与 R447 存档 `gen_J0_sum = 3215` **逐位相同**（同 prompt 同档同温度）⇒ 器具可复现。
- **CH8 无截断预算下界**：限长子句下 T2 真实思考 median **138.5** / max **211**（0 截断）⇒ 预算 128 必然截断；**无截断所需预算 ≥212**（现网 512 已不可再压）。

## 5. 结论与机制

- **prompt 侧限长思考不成立**：① 指令**不被遵守**（T2 真实思考长度 median 138.5 ≫ 目标 64，仅降 22.5%）；② 插入 28 字符本身**改变判决**（agree(T2,J0)=0.4444）——与「同输入⇒同字母」（R446）合起来说明判官对 prompt 逐字敏感；③ 只压预算 ⇒ 61.1% 截断 ⇒ 产品必然 fallback 远端 ⇒ **比不优化更贵**。
- **本地生成侧压缩通道已全部关闭**：R447（解码约束）+ R448（prompt 限长）双双因不等价而否。剩余未测的本地降本通道只在**预填充侧**（2764 tok / 10 调用，占判官成本 58%）与**调用合并**（判官+门各一次预填充）。
- 自纠披露：① 分析器 C6 曾把 `agree=0.0` 用 `or 1` 误判成 1.0 ⇒ 首版假红；已修并重跑。② C7 预注册断言「跨臂 prompt_n 相等」在臂定义层面不可满足（正是被消融的自变量改了 prompt 长度）⇒ 属判定项设计缺陷；按判据纪律**保留 C7 红**、单列 CH6 修正口径。

## 6. 诚实边界

1. 单模型档（`r1-distill-1.5b-q4km`）+ 单容器（`-c 4608`）；未测其它量化/更大模型档。
2. 语料 msg 全 ≤18 字符；prev 真值仅 3 种（**prev 面弱**，G2 只钉下界，未证明多样性充分）。
3. 口径 = 本地 llama-server 真值 token；**未**折算为用户可见的远端 API 计费，**未**测时延 KPI（T1 墙钟 13.67s vs J0 16.75s 仅为副产品读数）。
4. 未做远端 A/B（等价已红 ⇒ 无必要）；门通道（`local_turn_gate`，~130 tok/调用 ×7）本轮未测。
5. 无链跑 ⇒ **不写 `eval/capability/kpi.jsonl`**；零产品代码改动 ⇒ 无 AOT/单测对象（不触发 AOT 铁律）。
6. C6 首版假红与 C7 判定项缺陷均已留痕（§5 自纠），**不得宣称预注册全绿**。

## 7. 复现命令

```bash
python3 eval/rover/r448/r448_corpus.py     # 语料 + 四闸（~秒级）
python3 eval/rover/r448/r448_probe.py      # 真机 62 次调用（~14 min，起手闸 MemAvailable>=2650MB）
python3 eval/rover/r448/r448_analyze.py    # C1–C7 + CH1–CH8
python3 eval/rover/r448/register_r448.py   # registry/improvements/master-plan 落盘
```
