# R400 · rover 生成链 证据报告（分词器 / chat template / 采样 / 解码环）

- 轮次: **R400**（2026-09-14）；上游: R399（`4cabcc5`）；本轮: 规划入账 `f75e6f7` + 生成链落地 `9d2191a`
- 计划文档: `docs/plans/v0.26.0-r400-rover-generation-chain.md`（含实施记录 §8）
- 目标: 让 `agent.rover` 从「只有 `forward`（token→logits）」变成**文本进文本出**（分词器 → chat template → 采样 → 解码环），
  且每一步都有**独立实现 oracle** 的逐条对账与**带判别力读数的负控**。
- 结论: **链路已交付并通过对账**；本机 CPU 生成**不可交互**（0.0389 token/s），性能线属 R401/R402。

## 1. 对账读数（oracle = HuggingFace `tokenizers` 0.23.2，独立实现，非本仓代码）

| 夹具 | 条数 | 断言对象 | 结果 |
|---|---|---|---|
| `fixtures.jsonl` | 199 | 文本 → id 序列（逐 id 相等） | **199/199** |
| `pretok_fixtures.jsonl` | 199 | 文本 → 预分词分片（逐元素相等） | **199/199** |
| `stress_fixtures.jsonl` | 2000 | 确定性随机对抗文本（encode + 分片**双断言**） | **2000/2000** |
| `decode_fixtures.jsonl` | 405 | id 序列 → 文本（`skip_special_tokens` 两种口径） | **405/405** |
| `chat_golden.jsonl` | 12 | 对话 → prompt（jinja2 = transformers 同引擎同参数，**逐字节**） | **12/12** |

- **两条装载路径同摘要**：`tokenize --tables eval/rover/tokref/tables`（表快照，无需 4.2 GB 模型）与
  `tokenize /tmp/models/prover7b-q4km.gguf`（真机 GGUF 装载）读数**完全一致**（`pass=true`）：
  `tokens_sha256=6e5117ddc01e0cb3…`、`merges_sha256=cb5bed793622288a…`（与 GGUF 登记同值）、
  词表 102400（100000 正常 + 18 控制 + 2382 UNUSED）、合并 99757。
- **判定谓词表**（oracle **阶段隔离**探测，`eval/rover/tokref/tables/predicates.json`）：
  `\s` = **25 码点 = Unicode White_Space 全集**（全 BMP 穷举 + 增补候选）；
  Digits = `{Nd,Nl,No}` 全集（候选 1831 命中 1831，非候选取样负控 3920 例 **0 违规**）。

### 1.1 逐条对账（真机 GGUF 装载路径，原文）

```
tokenizer{spec=gpt2/byte-level gguf tokens=102400 merges=99757 tokens_sha256=6e5117ddc01e0cb3 merges_sha256=cb5bed793622288a source_gguf=1f6039c37ea41974}
fixtures_encode{file=fixtures.jsonl cases=199 pass=199 fail=0}
fixtures_pretok{file=pretok_fixtures.jsonl cases=199 pass=199 fail=0}
fixtures_stress_encode{file=stress_fixtures.jsonl cases=2000 pass=2000 fail=0}
fixtures_decode{file=decode_fixtures.jsonl cases=405 pass=405 fail=0}
done{command=tokenize.fixtures pass=true}
```

## 2. 负控读数（判定力**量化**，不是「跑红就算」）

统计口径: 只在**依赖合并表的样本**上统计（至少一个预分词片段被切成 ≥2 个 token）。
整片命中词表的文本与合并表无关，计入会稀释判别力 —— 这是 R399「空心指标」教训的直接应用。

| 变体 | 依赖合并样本 | 被检出 | 检出率 | 断言下界 |
|---|---|---|---|---|
| `merges` 乱序（集合不变，只改 rank） | 1814 | 753 | **41.5%** | ≥30% |
| `merges` 逆序 | 1814 | 1032 | **56.9%** | ≥40% |
| `merges` 清空 | 1814 | 1728 | **95.3%** | ≥90% |
| 空切分集（`SplitTokens=[]`） | — | 特殊符号文本 3 → 15 id | **必红** | 必红 |
| 朴素整片预分词（不做切分） | — | 判别 137 条 | **137/199** | ≥100 |

```
neg_control{kind=merges:shuffled dependent=1814 caught=753 rate=41.5 %}
neg_control{kind=merges:reversed dependent=1814 caught=1032 rate=56.9 %}
neg_control{kind=merges:empty dependent=1814 caught=1728 rate=95.3 %}
neg_control{kind=naive_pretok naive_pass=62 total=199 discriminated=137}
neg_control{kind=no_split_tokens baseline_ids=3 variant_ids=15 changed=True}
```

**负控当场抓到的真 bug**: 采样器首版 `NextU64` 把 RNG 状态拷贝进局部变量再 `ref` ⇒ 随机源**永不前进**（采样退化为恒定输出）。
由「平坦分布 300 次抽取必须出现 >5 个不同 id」的反向控制捕获，已修并保留为常驻测试（`RoverSamplerTests.Sampling_IsNotDegenerateArgMax`）。

## 3. 真机生成读数（7B Q4_K_M，2 vCPU，无 GPU）

prompt = `<｜begin▁of▁sentence｜>你是严谨的数学助手…<｜User｜>证明: 若 n 为偶数, 则 n^2 为偶数。<｜Assistant｜>`（37 token），
`--max-tokens 8 --temperature 0.7 --top-k 40 --top-p 0.95 --seed 12345`。

| 指标 | 读数 |
|---|---|
| prefill（37 token） | 783,384.5 ms（21.2 s/token） |
| decode 逐 token | 25,919.9 / 25,655.1 / 25,673.4 / 25,710.1 / 25,720.8 / 25,691.5 / 25,705.2 / 25,731.2 ms |
| ms_per_token | **25,725.9** |
| tokens_per_s | **0.0389** |
| 总墙钟（8 token） | 989,894.9 ms（16.5 min） |
| 峰值 RSS | 1,995,580 KB = **1.90 GiB**（ws_delta 2,013,544,448 B） |
| 流式字节 | 177,440,440,320 B = **165.2 GiB** ⇒ 3.943 **GB/token**（≈0.94× 模型体积）<br>（**R402 口径修正**：原写 ≈22.2 GB/token「≈5.3× 模型体积」是**分母口径错** —— 分子含 prefill 37 + decode 8 = **45 个 pass**，分母只除了 8 步 decode。按 token 数除才是 3.943 GB/token，与本节下文「每 token 流式扫 ≈4.0 GiB」自洽；见 `docs/reports/r402/io-attribution.md` §4.1） |
| 采样随机数消耗 | `draws=8`（1 draw/token，修复后行为） |
| 驱逐 | `evicts=0`（默认 pin 热集） |
| stop | `max_tokens`（未自然 EOS） |
| 生成文本 | `" 2 2 2 2"`（id 序列 `[207,17,207,17,207,17,207,17]`） |

- **与 R399 forward 读数交叉一致**: R399 引擎读数 1/2/4/8 token = 15.87/40.64/107.06/189.81 s；
  本轮 8 token 解码 = 205.8 s（8×25.7）—— 同一量级（差异来自 prompt 前缀 + 本轮 KV 更长）。
- **诚实边界（生成质量）**: 8 token 预算下模型输出为退化串（` 2 2 2 2`）。
  ⇒ 本轮**不宣称任何解法能力**；已证的是**链路机械正确**（分词/模板/采样/解码全部与 oracle 逐条相等 + 真机端到端能出 id 与文本）。
  文本质量与解法级能力需要**足量 token 预算**（≈512 token × 25.7 s ≈ 3.7 h/题）⇒ 归 R401 决策。

### 3.1 「远端 API vs 本机引擎」解法级对比（R400 首次可算）

| 后端 | token 吞吐 | 依据 |
|---|---|---|
| 远端 API（`solver=agent`，R399 真机批） | **470.2 tok/s**（26,375 tok / 56.09 s，35 题） | `data/probe/probe-agent-seed20260913.json` |
| 本机引擎（`solver=rover`，R400 真机） | **0.0389 tok/s**（25.7 s/token） | `data/probe/r400/rover-gen-7b.json` |
| 倍差 | **≈12,088×** | — |

- 换算: 一道需要 ≈4,396 token 的题 ⇒ 本机引擎 ≈ **31.4 h/题**，远端 API ≈ **9.3 s/题**。
- **结论（诚实）**: 在本机 2 vCPU / 无 GPU / 每 token 流式扫 ≈4.0 GiB 的条件下，
  rover **不是交互级解法后端**；R400 交付的是「生成链正确且可对账」这一**前置条件**。
  解法级 KPI 对比要等 R401/R402（批 prefill / 线程 / mmap 策略）把吞吐抬到可测区间才成立。

## 4. 本轮 5 处实测修正（均为「看起来对」的失效形态）＋ R402 复核追加 1 处

| # | 现象 | 根因 | 修法 |
|---|---|---|---|
| ① | 增补平面字符被静默过量匹配 | .NET `Regex` 按 **UTF-16 码元**解析字符类，`𐐀-𐑏` 被拆成孤立代理项 + 反向区间 | 生成器把正则机器解析成**标量区间表**，C# 侧标量扫描器消费（禁用 .NET Regex） |
| ② | `中अआ文` 被切成 3 片 | CJK 正则原文顺序 `一-龥` `ࠀ-一` `가-퟿` **非升序** ⇒ 二分查找漏判 | 生成器**归一化**（排序 + 合并并集）+ 自检项「区间严格升序互不重叠」 |
| ③ | `：\u3000””\u3000` 尾片切分错误 | `\s?[类]+` 的空白前缀**需要回溯**（贪婪吞空白后若不是类字符，须退回不吞，把该空白字符当类成员） | `MatchClassRun` 实现回转义 |
| ④ | 谓词表把 Zs 类空白误判为「非 `\s`」 | 用**整条流水线**探测单条谓词，后续 CJK 阶段二次切分干扰判断 | 改为 oracle **阶段隔离探测**（只喂单个 Split/Digits 句柄） |
| ⑤ | 特殊符号编码结果与 oracle 不一致 | 误以为切分集 = `special=true` 的 3 个 | 实测切分集 = `added_tokens` **全体 18**；`special=true` 的 3 个只影响 `decode(skip_special_tokens=true)` |
| ⑥ | **（R402 复核追加）** 流式字节被报成 ≈22.2 GB/token（≈5.3× 模型体积），与本报告下文的「≈4.0 GiB/token」自相矛盾 | 台账口径错：分子含 37 prefill + 8 decode 共 45 个 pass，分母只除 decode 的 8 步 | 改为按 token 数除 = **3.943 GB/token**；引擎侧同步加 `streamed_bytes_per_pass`（分母 = pass 数）作为**唯一口径**，并配单测钉死分母语义 |

## 5. 交付物

| 类别 | 落点 |
|---|---|
| 代码 | `src/agent.rover/token/{ByteUnicode,Pretokenizer,BpeTokenizer,ChatTemplate,TableSnapshot,TokenizerAssets.g.cs}`、`src/agent.rover/infer/Sampler.cs`、`src/agent.rover/cli/GenerateCli.cs`、`RoverCli.cs`(分派)、`src/agent/agent.csproj`(共享源) |
| 资产 | `eval/rover/tokref/`（`tables/` 表快照 + `fixtures.jsonl`/`pretok_fixtures.jsonl`/`stress_fixtures.jsonl`/`decode_fixtures.jsonl`/`chat_golden.jsonl`/`manifest.json`） |
| 生成器 | `scripts/rover_gen_tokenizer_assets.py`、`scripts/rover_probe_oracle_predicates.py`、`scripts/rover_build_tokenizer_fixtures.py` |
| 测试 | `src/agent.tests/RoverTokenizerTests.cs`(16) + `RoverSamplerTests.cs`(8) = **22 条** |
| 探针 | `eval/probe/run_probe.py` → `solver=rover`（同题同判定器；读数标注 `budget_limited=true`） |
| 读数 | `data/probe/r400/rover-gen-7b.json`、`data/probe/rover_engine_kpi.jsonl` |

## 6. 复现命令

```bash
export DOTNET_ROOT="$HOME/.dotnet"; export PATH="$HOME/.dotnet:$PATH"
# 离线对账（无需 4.2 GB 模型；表快照随仓库）
dotnet run --project src/agent.rover/agent.rover.csproj -c Release -- tokenize --tables eval/rover/tokref/tables --selftest
dotnet run --project src/agent.rover/agent.rover.csproj -c Release -- tokenize --tables eval/rover/tokref/tables --fixtures
dotnet run --project src/agent.rover/agent.rover.csproj -c Release -- tokenize --tables eval/rover/tokref/tables --neg-control
# 真机（需 GGUF）
dotnet run --project src/agent.rover/agent.rover.csproj -c Release -- tokenize /tmp/models/prover7b-q4km.gguf --fixtures
dotnet run --project src/agent.rover/agent.rover.csproj -c Release -- generate /tmp/models/prover7b-q4km.gguf \
  --chat --system "你是严谨的数学助手, 先给推理再给结论。" --prompt "证明: 若 n 为偶数, 则 n^2 为偶数。" \
  --max-tokens 8 --temperature 0.7 --seed 12345 --json data/probe/r400/rover-gen-7b.json
# 夹具/资产再生成
python3 scripts/rover_probe_oracle_predicates.py --tokenizer-json <tokenizer.json>
python3 scripts/rover_gen_tokenizer_assets.py --tokenizer-json <tokenizer.json> --check
python3 scripts/rover_build_tokenizer_fixtures.py --tokenizer-json <tokenizer.json> --gguf /tmp/models/prover7b-q4km.gguf
```

## 7. 诚实边界（汇总）

1. 本机 2 vCPU / 无 GPU / 每 token 流式扫 ≈4.0 GiB ⇒ 生成**不可交互**（25.7 s/token，0.0389 tok/s）；
   本轮交付「链路正确 + 可对账」，性能线属 **R401/R402**。
2. 8 token 预算下输出为退化串 ⇒ **不宣称解法能力**；`solver=rover` 的读数一律带 `budget_limited` 标注。
3. chat template 仅支持 `system/user/assistant` 子集；工具调用与 Jinja 全量属 **R403**。
4. 采样器**不含**重复/存在/频率惩罚（已列入计划 §6 排除项）。
5. oracle 依赖 `tokenizers` 0.23.2 与权威 `tokenizer.json`（经 `hf-mirror.com` 取得）；两者 sha256 已登记，
   夹具与表快照随仓库入库 ⇒ **对账可离线复跑**，但**再生成**需要网络与 HF 依赖。
