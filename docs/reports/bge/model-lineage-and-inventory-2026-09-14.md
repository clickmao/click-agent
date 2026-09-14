# bge 模型身份·血统·本机清点（2026-09-14）

> 触发（用户逐字）：`优化版那个不是20多m么？` → `因为都删除了只保留了一个v10版本` → `先确定它是不是优化过的` → `我们做词法融合跑分变高的那个版本去哪了？`
> 全部结论取自本机落盘件（env / 文件哈希 / 元数据 / 下载器脚本 / 报告 / 缓存 / 登记表），非记忆。

## 1. 三句话结论

1. **链上真身** = `~/.agentframework/models/bge-q8.gguf`：26,472,640 B（**25.2 MB**），sha256 `5a88d266870fbd27c6f329df60de80e2d4cf3bbd5e6f080bd5c1b2e5abb12039`，
   元数据 `name=bge-small-zh-v1.5` / `block_count=4` / `embedding_length=512` / `head_count=8` / `q8_0`。
   产品侧指向它的是 `.env.local:5` 的 `AGENTFRAMEWORK_BGE_MODEL`（env 覆盖代码默认 ⇒ **默认值≠运行值**）。
2. **它不是"自研优化产物"**：本机唯一的 bge 权重来源是 `/tmp/dl_bge.py` —— 一个**下载上游现成 GGUF** 的脚本（在候选仓库里取 < 150 MB 中最小的那个，无任何转换/量化/剪枝步骤）；
   全仓检索 `convert_hf_to_gguf` / 剪枝 / 蒸馏 / 本地量化 ⇒ **0 命中**；该文件 mtime = `2026-09-06 23:45`（下载当日），此后所有"优化"轮次都只产出**外挂适配器**，未改写权重。
   形态与官方 `bge-small-zh-v1.5` 的 Q8_0 一致。
   - **诚实边界**：上游 LFS 哈希取不到（hf-mirror 返 `{"error":"Invalid username or password."}`、huggingface.co 无响应）⇒ **无法做逐字节上游对账**；"非自研产物"由上述本机痕迹链支撑，不由上游背书。
3. **"词法融合跑分变高的那个版本"不是一个权重文件，而是产品代码里的融合层**：`src/agent.rag/FusionRecall.cs`（12,247 B）+ `src/agent.rag/RAGConfig.cs` 的 `Fusion` 配置，
   DI 冻结点 `src/agent/extensions/ServiceCollectionExtensions.cs:238` = `Enabled=true, K0=10, DenseWeight=1.0, LexicalWeight=1.0`。**它一直在产品里跑，从未被删**（git 引入于 `cd8feeb`）。

## 2. 两条口径必须分开（本轮定位到的登记缺口）

| 口径 | dense 路 | r@10 | 命中 | 性质 |
|---|---|---|---|---|
| **产品真身** | small（25.2 MB，链上） | **0.7833** | 94/120 | 实跑形态；Δ vs small 单路 **+18 条**，配对 McNemar **p=4e-05** |
| 评测对照 | base（110 MB） | 0.8500 | 102/120 | **非产品读数**（该权重已删） |

单路读数：lex **0.7500** / dense-small **0.6333** / dense-base **0.7417**。

- 旧注释 `0.6333 → 0.8500 (+13 条, p=0.0023)` 是**跨基座混算**：`0.6333` 是 small 单路，而 `+13 条` 是相对 **base 单路**（102−89）。产品真实的净增益是 **+18 条**（94−76）。
  ⇒ 已在三处订正：`FusionRecall.cs`（类注释读数表）、`RAGConfig.cs:24-29`、`ServiceCollectionExtensions.cs:235-240`。
- 既有 21 变体网格里**从来没有 `lex+small` 这一行**（全部含 base）。本轮补测：
  脚本 `eval/bge/fusion_lex_small.py` → 产物 `eval/bge/results/fusion-lex-small-2026-09-14.json`。
  采信前提 = **先复现控制组**：`lex+base k0=10 w=1:1 = 0.8500(102/120)` 与登记网格**逐位一致**，否则本脚本读数不采信。

## 3. 删除记录（用户令 2026-09-14：除真身外都删，避免误认如 110m 那个）

| 文件 | bytes | sha256 | 处置 |
|---|---|---|---|
| `~/.agentframework/models/bge-base-zh-v1.5-q8.gguf` | 110,001,568 | `893a0f07100c…` | 已删 |
| `/tmp/models/bge-base-zh-v1.5-q8.gguf` | 110,001,568 | `893a0f07100c…` | 已删（同源副本） |

登记：`eval/rover/registry/deleted-models.jsonl`（追加不覆盖，含 bytes/sha256/理由/用户令原文）。

**保留且必须保留**（否则 0.8500 那组读数会失去可复现性）：
- 权重：`bge-q8.gguf`（真身）
- 向量缓存：`data/bge/cache/bge-base-zh-v1.5-q8__fuse_corpus_*_1299_3f92dd05.f32`、`...__fuse_queries_*_120_3f92dd05.f32`、`bge-q8__fuse_*_3f92dd05.f32`
- 秩文件：`eval/bge/ranks/{bge-base-zh-v1.5-q8.json,bge-small-zh-v1.5-q8.json,fusion-best.json}`

**删后复现验证**：`fusion_lex_small.py` 重跑 **exit 0 / 34 s**，控制组 `lex+base = 0.8500 (102/120)` 逐位一致
⇒ **0.8500 的证据没被删掉**，只是不能再跑 base 前向（如需重跑须按同一上游路径重新下载，网络受限时不可得）。

## 4. 连带处置（不让无人值守作业静默失效）

| 处置 | 位置 | 原因 |
|---|---|---|
| 默认路径改真身 | `src/agent.llamacpp/LlamaCppTextEmbedder.cs:31`：`bge-base-zh-v1.5-q8.gguf` → `bge-q8.gguf` | 旧默认在 env 未设时 ⇒ `IsAvailable=false` ⇒ 静默降级 `NullTextEmbedder`（空心向量） |
| base 臂降级为**只读缓存** | `eval/bge/fusion.py:172-180`（缓存缺失即 assert 失败） | 绝不静默用 small 顶替 base —— 那正是"跨基座混算=空心指标" |
| cron `79b866b5097d`（bge-gate-fusion）**pause 勿删** | `every 360m`，其 KPI 依赖 base 前向 | 依赖已删权重 ⇒ 不暂停会开始报错/噪声。训练 cron `a6b0d3aaf416` 此前已 pause |

仍引用 base 路径、需重下载才能复跑的脚本（清单，供后续轮次按需处理）：
`scripts/r404_bge_parity_probe.py`、`scripts/bge_idle_train.sh`、`scripts/bge_gate_fusion_auto.sh`、`eval/bge/auto_cycle.py`、`eval/bge/throughput_llama.py`、`eval/bge/pooling_equivalence.py`。

## 5. 验收证据

- 全量测试：**1087 通过 / 0 失败 / 0 跳过（32 s）**
- AOT 发布：**0 IL 警告**（规范命令，不带 `-p:PublishAot`）
- 复现链：`fusion_lex_small.py` exit 0；控制组 `lex+base=0.8500(102)` 与登记网格逐位一致

## 6. 本档未覆盖（诚实边界）

- 上游逐字节对账不可得（网络受限，见 §1.2）。
- `lex+small` 只在**单一冻结集**（1299 语料 / 120 查询，分辨率 1 条 = 0.83pt）上测过；`k0=20 w=1:1` 得 0.7917（95/120，+19 条）比冻结配置高 **1 条 = 噪声地板** ⇒ 不构成改配置的理由（1 条级不当硬判决）。
- 真实用户检索标注仍未开启（训练对全部为 LLM 合成），故以上均为**离线冻结集**读数。
