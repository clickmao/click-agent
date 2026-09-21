# RF0006 · 三值量化压缩 gguf 体积（独立调研项目）

> 缘起（用户令，2026-09-21 逐字）：**「新增独立调研项目：利用三值量化将现有gguf体积压缩」**
> 定级：**独立调研面**，与主线（RF0004 三能力 / RF0005 完成协议）并行 —— **不占主线轮次 · 零 `src/` 改动 · 不新增夹具**；
> 器具全部复用上游件与既有夹具：`llama-quantize --dry-run`（上游自带投影器具）· `llama-cli`（连贯性探针）· 判别位夹具（R577 判据）· `tools/roundcheck/`。
> 关联：`docs/evidence/RF0006/ternary-recon-readings.md`（本轮原始读数）· `docs/plans/RF0005-completion-protocol.md`（§4 排期映射，本面为并行独立轨）· `eval/capability/baselines.json`

状态：**活计划**（§3 判决随真机读数刷新；历史读数一律不改） ｜ 建立轮次：**R608（调研首轮，2026-09-21）** ｜ 机检口径：`llama-quantize --dry-run` + 判别位夹具 + `status_gen.py --check`

---

## §0 目标与验收（全部机检）

**目标**：压缩现有 gguf 的体积/内存占用，且**判别位能力不降**。

| # | 判据 | 阈值 | 现读数 | 状态 |
|---|---|---|---|---|
| 1 | 目标模型体积 | ≤ 现役 `LFM2.5-VL-3B-Q4_K_M` 的 **70%**（≤1,117.8 MiB；现役 1,674,455,072 B = 1,596.88 MiB） | **QR1 实测达：下载件 1,137,806,656 B = 68.0%**（逐字节 = 镜像 API 原值）；R3-Q2_K 投影 1,036.03 MiB（64.9%） | **① 达** |
| 2 | 判别位能力 | `acc = 1.000` ∧ `假跳 0/14`（R577 判据，**不得放宽**） | 现役件 1.000 / 0/14；三值 PTQ 件 **探针全乱码**；原生件 QR1 冒烟（**主线运行时**）**证据已降级** ⇒ 待 QR1b/QR2 用厂商 fork 重验 | **未达标（待 QR2）** |
| 3 | 产品可加载 | 本地推理 pin 支持该 ggml 类型；AOT/零反射面不受影响 | **上游 b11065 不含 Hadamard 运行时**（vendor：`PQ2_0`/`PTQ1_0` 被拒为未知类型、`Q2_0` 静默乱码）⇒ **产品 pin 必须换厂商 fork 二进制** | **否（须换运行时）** |
| 4 | 可复跑 | 每条读数三段绑定：`source_path` + `source_sha12/尺寸` + `check_cmd` | 见 §6 | **已绑定** |

---

## §1 现状（真机清点 2026-09-21）

**五件 gguf，合计 4,518,679,232 B（4.21 GiB）**：

| 件 | 字节 | MiB | 用途 |
|---|---|---|---|
| `lfm25vl3b/LFM2.5-VL-3B-Q4_K_M.gguf` | 1,674,455,072 | 1,596.88 | **现役判别位**（文本塔） |
| `lfm25vl3b/mmproj-LFM2.5-VL-3B-Q8_0.gguf` | 583,109,984 | 556.10 | 视觉投影（VL） |
| `r1-distill-qwen-1.5b-q4km.gguf` | 1,117,320,800 | 1,065.56 | 留盘对照 |
| `qwen2.5-1.5b-instruct-q4km.gguf` | 1,117,320,736 | 1,065.56 | 留盘对照（本轮**探针基准件**） |
| `bge-q8.gguf` | 26,472,640 | 25.25 | 向量件 |

主机（真读）：`nproc`=2 · `MemTotal` 3,747,744 kB · `MemAvailable` 2,983,272 kB · 磁盘 `50G/38G/**9.6G free (80%)**` · 无 GPU。
上游件：llama.cpp **b11065**（`llama-b11065-bin-ubuntu-x64.tar.gz`，16.1 MB）解包于 `/tmp/llamatq/`；产品 `AGENTFRAMEWORK_LLAMA_BIN` **现盘未设**、`llama-server` 不在盘（R606 时代曾有）⇒ 见 §6 器具闸。

---

## §2 上游能力核实（逐字 · 带出处）

1. `llama-quantize --help`（b11065）类型表逐字：`Q1_0 : 1.125 bpw quantization` · `Q2_0 : 2.25 bpw quantization (group 64)` · `TQ1_0 : 1.69 bpw ternarization` · `TQ2_0 : 2.06 bpw ternarization` · `IQ1_S : 1.56 bpw` · `Q2_K` 等。
2. **`--dry-run`**（同 build 自带）：`calculate and show the final quantization size without performing quantization` ⇒ **零写入投影器具**（本轮实测单次 122 ms）。
3. `--allow-requantize`：源为已量化件时必需；上游自带警告「can severely reduce quality compared to quantizing from 16-bit or 32-bit」。
4. 维护者结论（llama.cpp issue **#15193**，CISC，2025-08-09）逐字：**"Ternary quants are only meant to be used on models trained for it, like BitCPM4-1B, you will get utter garbage on anything else."** 同 issue 的报障（Qwen3-4B→TQ1_0「llama-server outputs messy contents」）与本轮真机结果**同形**。
5. TQ 系**不吃 imatrix**（llama.cpp discussion **#17393**：TQ1_0/TQ2_0 "Does not use importance matrices"）⇒ 混精路线里 imatrix 只能作用于 K/IQ 系张量。
6. `Q1_0`/`Q2_0` 为 **2026 新增**（PR **#24448** CPU 2026-06-11 合入；PR **#25707** CUDA 2026-07-30），动机 = 原生三值族 `Ternary-Bonsai-{1.7B,4B,8B,27B}`；Q2_0 = group-64、2.25 bpw。

---

## §3 判决（本轮真机，2026-09-21）

### 3.1 对现有 gguf 直接三值重量化 = **能力归零**（不是「差一点」）

剂量-响应：`qwen2.5-1.5B-Instruct-Q4_K_M`（1,065.56 MiB）→ 各型，**同一 3 探针**（P1 算术 / P2 判断 / P3 中译英），`--temp 0`、`-n 16~20`。

| 类型 | 落盘文件 | 占原档 | 省 | tool 报 (BPW) | P1 | P2 | P3 | 判决 |
|---|---|---|---|---|---|---|---|---|
| Q4_K_M（原档） | 1,117,320,736 B | 100% | — | — | `2 + 3 * 4 = 14` ✓ | `不成立。` ✓ | `The weather is very good today.` ✓ | **基准** |
| Q3_K_M | 924,455,968 B (881.63 MiB) | 82.7% | 17.3% | 875.96 MiB (4.13) | ✓ | ✓ | — | 可用 |
| Q2_K | 752,880,160 B (718.00 MiB) | 67.4% | 32.6% | 712.33 MiB (3.36) | `2+3*4=2+12=14` ✓ | `不成立。` ✓ | — | 可用 |
| TQ1_0 | 605,611,552 B (577.56 MiB) | 54.2% | 45.8% | 571.88 MiB (2.70) | ✗ 乱码 | ✗ 乱码 | — | **不可用** |
| TQ2_0 | 667,026,976 B (636.13 MiB) | 59.7% | 40.3% | 630.45 MiB (2.98) | ✗ 乱码 | ✗ 乱码 | — | **不可用** |
| Q2_0 | 697,734,688 B (665.41 MiB) | 62.4% | 37.6% | 659.74 MiB (3.11) | ✗ 乱码 | ✗ 乱码 | — | **不可用** |
| Q1_0 | 415,033,888 B (395.81 MiB) | 37.1% | 62.9% | 390.13 MiB (1.84) | ✗ 乱码 | — | — | **不可用** |

> 落盘文件 > tool 报「quant size」为元数据/对齐开销；两列并报，**禁混用**。
> TQ1_0 与 TQ2_0 的输出**逐字相同** —— 现象记录在案，**不归因**（未做单变量分离）。
> **三值的代价不是体积**：Q2_K 只比 Q2_0 大 8%（0.25 BPW）、比 TQ2_0 大 13%，却保住能力；三值把能力打到零。

### 3.2 现役件投影（`--dry-run`，零写入）

`LFM2.5-VL-3B-Q4_K_M`（1,596.88 MiB）⇒ Q1_0 532.61（−66.6%）· TQ1_0 695.87（−56.4%）· TQ2_0 804.71（−49.6%）· Q2_0 859.14（−46.2%）· **Q2_K 1,036.03（−35.1%）** · Q3_K_M 1,295.67（−18.9%）。

**视觉塔不可压（硬失败）**：`mmproj`（Q8_0, 556.10 MiB）→ Q1_0 报 `v.blk.0.ffd_down.weight - ncols 4304`（非 64 整除）⇒ **556.10 MiB 为不可压底座**，压缩率上界由它约束。

### 3.3 体积 ⇒ 显存论（Bonsai 家族 · **Bonsai 2 27B**）｜用户令 2026-09-21

> 本节回答「三值化为何能有效缩减体积、并因此减少 GPU 显存」。**Bonsai 2 27B 全部数据引自 `prism-ml/Ternary-Bonsai-2-27B-gguf` 模型卡（2026-09-21 经 hf-mirror 取，逐字来源见证据件 R8）**；显存/吞吐是 vendor 表读数，本机**无 GPU** ⇒ 一律「引用/投影」，不得当本机实测。

**A. 位宽 ⇒ 体积 ⇒ 显存（真值链）**

| 表示 | 真实 bits/weight | 体积 | 相对 FP16 |
|---|---|---|---|
| FP16（基线） | 16.0 | ~54 GB | 1.0× |
| 三值 g128（理想） | 1.72 | 5.8 GB | ~9.3× |
| **GGUF `PTQ1_0`**（稠密 trits） | **1.75** | **5.95 GB** | **~9.0×** |
| **GGUF `PQ2_0`**（2-bit 槽） | **2.13** | **7.21 GB** | **~7.5×** |

- 原理：权重 ∈ {−1,0,+1}，每 **128** 权重共享一个 FP16 scale ⇒ 承载 `log₂3 ≈ 1.585` bit 信息 ⇒ 有效 ~1.71 bpw；矩阵先做**分块 Hadamard 旋转**（block 1024，固定 ±1 符号）再取三值，运行期对激活做同变换（= ITQ3_S 那条「旋转域压离群」机制的真机落地）。
- **「低位宽标签」对比（vendor 明确指出）**：常规 `IQ2_XXS` 标称 2-bit，**真实 2.8 bpw / 9.4 GB**；`UD-Q4_K_XL` 标称 4-bit，真实 5.2 bpw / 17.6 GB。三值件是**端到端**低位宽（embeddings / attention / MLP / LM head 全覆盖，无高精度逃生舱）——与本仓 §3.1 的对照一致：K 系因保留 embedding/output 高精，标称 1.125 bpw 实测 **1.84 bpw**。
- 显存 = **权重 + KV cache + 计算缓冲 + CUDA 上下文**。权重压到 1/9 后，**KV 与上下文成为主导项** ⇒ 必须并列 KV 量化与上下文档位预算（下表）。

**B. 显存预算（Bonsai 2 27B；真实 arch：64 层 = 16 全注意力 + 48 线性；全注意力 4 KV heads × head_dim 256 ⇒ 32,768 elem/token）**

| 上下文 | KV fp16 | KV q8_0 | KV q4_0 | PTQ1_0 + q8_0-KV | PTQ1_0 + fp16-KV | PQ2_0 + q8_0-KV |
|---|---|---|---|---|---|---|
| 4K | 0.27 GB | 0.14 GB | 0.08 GB | **6.1 GB** | 6.2 GB | 7.4 GB |
| 32K | 2.15 GB | 1.14 GB | 0.60 GB | **7.1 GB** | 8.1 GB | 8.4 GB |
| 128K | 8.59 GB | 4.56 GB | 2.42 GB | **10.5 GB** | 14.5 GB | 11.8 GB |
| 256K | 17.18 GB | 9.13 GB | 4.83 GB | **15.1 GB** | 23.1 GB | 16.3 GB |

- 262K 上下文可落地，靠的是 **75% 线性注意力层**：KV 只由 16/64 层产生，线性层状态 ~75.5 MB 且**与上下文无关**。即便如此，fp16-KV 在 256K 仍达 17.18 GB ⇒ **长上下文时 KV 主导**（q8_0-KV 降到 9.13 GB）。
- **未计入**：CUDA 上下文 + 计算缓冲（~0.3–1.5 GB，随 batch/ubatch）；vision tower 0.63 GB（Q8_0，仅图像输入时驻留）。
- **「端到端低位宽」的诚实边界**（vendor 原文）：**26.2M 参数（占语言模型 0.0976%）仍以高精度保存**——线性注意力层的循环态通路 + 归一化权重；vendor 称这部分**已计入** 1.72 bpw 口径。即三值覆盖的是 embeddings / attention / MLP / LM head，而非「全部张量」。

**C. 卡型分级（vendor 实测 `tg128 / pp512` tok/s，batch 1 · depth 0 · 无视觉塔；**非本机读数**）**

| 平台 | PQ2_0 TG128 | PQ2_0 PP512 | PTQ1_0 TG128 | PTQ1_0 PP512 | 判读 |
|---|---|---|---|---|---|
| RTX 5090 (32 GB) | **129.9** | 3893 | 120.5 | 1805 | 256K 上下文 + 大 batch 有余量 |
| RTX PRO 6000 Blackwell | 124.8 | **4020** | 117.9 | 1972 | 同上 |
| H100 SXM (80 GB) | 113.9 | 2830 | 86.9 | 1237 | 多并发服务 |
| RTX 6000 Ada (48 GB) | 82.8 | 2431 | **90.4** | 1657 | Ada 代 PTQ1_0 更快 |
| RTX 4090 (24 GB) | 81.2 | 3124 | **91.1** | 1645 | 单卡 256K（q8_0-KV 15.1 GB） |
| L40S (48 GB) | 74.4 | 2868 | **81.8** | 1543 | 同上 |
| A100 SXM (80 GB) | 73.9 | 1328 | 54.7 | 706 | 提示处理弱 |
| L4 (24 GB, 72 W) | 29.8 | 777 | **32.1** | 467 | 8 GB 级预算实际落点 |
| Apple M5 Pro (Metal) | 28.1 | 387 | — | — | 7.2 GB 驻留 |
| Apple M5 Max (Metal) | 47.0 | 765 | — | — | 27B 在笔记本可交互 |

- **8 GB 档判读**：4K–32K 上下文（PTQ1_0 + q8_0-KV ⇒ **6.1–7.1 GB**）在 8 GB 卡上可行；128K 需 12–16 GB；256K 需 24 GB。
- `PTQ1_0` 在 **Ada 代与 L4** 解码更快（内存是瓶颈时），`PQ2_0` 在 H100/A100/Blackwell 与**所有**平台的提示处理上更快；能耗 2.0–4.3 J/tok（M5 Pro 解码 27.5 W GPU rail，对照 NVIDIA 板功 300–455 W）。
- 运行配方（vendor 原文）：`-ngl 99 -fa on -c 32768 --temp 1.0 --top-p 0.95 --top-k 20`；`-c` 最大 **262144**。

**D. 质量-体积前沿（vendor 自报 14 个 thinking 基准平均；**不当本仓读数**）**

| 变体 | 真实 bpw | 体积 | 基准均分 | vs FP16 | 智能密度 D=log₂(...)/GB |
|---|---|---|---|---|---|
| Qwen3.8-27B FP16 | 16.0 | 54 GB | 86.32 | 100% | 0.053 /GB |
| UD-Q4_K_XL（"4-bit"） | 5.2 | 17.6 GB | 85.18 | 98.7% | 0.156 /GB |
| IQ2_XXS（"2-bit"） | 2.8 | 9.4 GB | 72.59 | 84.1% | 0.199 /GB |
| **Bonsai 2 27B** | **1.72** | **5.9 GB** | **84.78** | **98.2%** | **0.460 /GB** |

⇒ 三值的价值不在「同尺寸更省」，而在**同等能力下更省**：1.72 bpw 拿到 FP16 的 98.2%，比常规 2-bit 件高 **12.19 分**而体积只有其 63%；比 4-bit 件小 **3 倍**、只差 0.4 分。智能密度 **2.3×** 于最强的常规低比特件。

**E. 与本项目判决的关系（一致性）**

- 常规低比特（Q2_K/Q3_K）＝ PTQ：能保能力，但到不了 1.7 bpw；三值要到 1.7 bpw **必须原生训练**（§3.1 已证：对现有件直接三值 = 乱码；文献 HGF 2602.05269 亦报 1.58-bit 需选择性低秩修正才稳定）。
- 故本项目结论为：**「三值压现有件」= 否；「三值换原生件」= 是**——收益 9× 体积 / 98.2% 能力（vendor 自报，本仓待 QR2 判据验证）。

**F. 边界与风险（不得省略）**

1. **运行时是硬约束（vendor 逐字）**：「**Stock llama.cpp will not run these files. It rejects `PQ2_0` and `PTQ1_0` as unknown types, and it loads `Q2_0` without any warning and produces garbage, because it has no Hadamard activation runtime. Use a binary from the fork.**」⇒ ①本仓 QR1 在主线上游 `b11065` 上跑的 `Ternary-Bonsai-4B-Q2_0_g64` 3/3 冒烟**正落在这条「静默劣化」路径**（缺 Hadamard 激活变换）⇒ **该冒烟的能力部分证据降级**：体积/内存读数仍有效（与运行时无关），**能力读数无效**；②凡涉及能力（判别位判据 QR2、混精对照 QR3）**必须用厂商 fork 二进制**；③fork 亦发布 **linux x64 CPU 构建** `llama-prism-b10709-9a9394a-bin-ubuntu-x64.tar.gz`（17.1 MB）⇒ **本机无 GPU 也可执行 QR1b/QR2**（已起 QR1b 成对对照：fork vs mainline）。
2. 本机**无 GPU**（MemTotal 3.57 GiB）：上表显存/吞吐全为**引用/投影**，不得当本机实测；本机唯一有效实测 = 体积（逐字节：4B `1,137,806,656 B`）+ 峰值 RSS **1.27 GiB**。
3. 质量数字为 vendor 自报 + 其 fork 运行时实测；本仓仅 3 探针冒烟（QR1，且已降级）⇒ 判别位判据（QR2）未跑，**不得声称能力等价**。
4. KV 不随权重压缩 ⇒ 长上下文必须同时开 KV 量化（q8_0/q4_0）并做档位预算，否则收益被 KV 吃掉。
5. 许可 Apache-2.0；vision tower 单独 0.63 GB（仅图像输入时驻留）。
6. **可复跑来源**：模型卡 `hf-mirror.com/prism-ml/Ternary-Bonsai-2-27B-gguf`（README 全文 + 逐字节文件表见证据件 §R8）；fork `github.com/PrismML-Eng/llama.cpp`（release tag **`prism-b10709-9a9394a`**，2026-09-18）；`github.com/PrismML-Eng/Bonsai-demo`（whitepaper / 运行脚本，vendor 声明的唯一权威运行源）；基座配置 `hf-mirror.com/Qwen/Qwen3.8-27B/raw/main/config.json`（64 层 = 16 全 + 48 线性、4 KV heads、head_dim 256、max_position 262144、vocab 248320）。

---

### 3.4 它的「重训练」方案是什么 · 本地可行性判定｜用户令 2026-09-21

**A. 方案定性（逐字出处，禁推断）**

| 命题 | 证据（逐字/出处） |
|---|---|
| **不是从头预训练** | 旧版白皮书 §2.3：「BitNet and its 1.58-bit successor … avoids the quality collapse only by **pretraining the network from scratch** directly in the low-bit regime … discards every existing pretrained model」；「Bonsai takes the opposite path from BitNet: it **starts from an off-the-shelf pretrained model and moves it into a binary or ternary representation**」 |
| **架构不变，只换表示** | Bonsai 2 27B 白皮书 §1：「uses the **same hybrid-attention architecture as Qwen3.8-27B**」；Ternary-Bonsai-27B 模型卡：「Derived from Qwen3.6-27B … (**architecture unchanged**)」 |
| **表示 = 固定旋转基三值 + 分组 FP16 scale** | 每 128 权重共享 1 个 FP16 scale；`w_i = s_g·t_i`，`t_i ∈ {−1,0,+1}` ⇒ 理论 1.71 bpw；**blockwise Hadamard 旋转（block 1024，固定 ±1 符号）**，运行时在**激活侧**做对应变换 |
| **≈99.9% 参数入低位宽** | 仅 **0.0976%（26.2 M 参数，bf16 52 MB）** 保高精：线性注意力 `in_proj_a/in_proj_b/conv1d/A_log/dt_bias/norm` + 各 layernorm；1.71 → **1.72 bpw**（含高精张量） |
| **算法本体未公开** | 1-bit 白皮书 §3：「This foundation comes from **proprietary Caltech intellectual property**」；三份 techreport（`bonsai-2-27b` / `bonsai-27b` / `1-bit-bonsai-8b`）只披露**格式 / 体积 / 吞吐 / 评测**，**无数据集、无优化步骤、无算力**；引用仅 `prismml.com`（无 arXiv） |
| **发布工件 = 权重 + 推理运行时** | `PrismML-Eng/llama.cpp`（fork，CUDA/Metal/HIP/CPU）+ MLX 包；`Bonsai-demo/scripts/` 全为 build / download / run / server / KV-bias / MLX 生成脚本，**无任何权重转换或训练脚本** |

**B. 本地可行性判定（本机实测规格 vs 需求）**

| 面 | 需求（由公开数字推） | 本机（2026-09-21 实测） | 判定 |
|---|---|---|---|
| 教师件 | Qwen3.8-27B FP16 = **53.8 GB** | RAM 3.57 GiB · 磁盘空 7.5 GB | **装不下（差 ≥7×）** |
| 若含梯度的转换/恢复 | 权重+梯度+Adam ≈ **215 GB**（fp32 master 53.8 + m 53.8 + v 53.8 + grad 53.8） | 无 GPU · 2 vCPU | **不可及（10^4–10^5）** |
| 复现入口 | 算法未公开（专有 IP） | — | **无入口** |
| 使用其结果（推理） | 4B PQ2_0 **1.00 GiB** · 8B PQ2_0 2.03 GiB · 27B PQ2_0 6.67 GiB | RAM 3.57 GiB | **4B/8B 可跑；27B 不可（超 RAM）** |

⇒ **两句话结论**：①**复现其 27B 转换/重训练 ⇒ 本地不可行**（算法未公开 + 工件装不下 + 算力差数量级）；②**使用其结果 ⇒ 4B/8B 档本地可行，27B 档本地不可行**（本机无 GPU、RAM 3.57 GiB）。

**C. 唯一有意义的本地切片（可执行替代，非复现其 IP）**

- 用公开小模型（≤0.3B）在 CPU 上做**玩具级机制复现**：blockwise Hadamard 旋转 → g128 三值 → 无梯度 scale 拟合（或小步恢复），与「**不旋转直接三值**」构成对照臂。
- 判据：同体积下「旋转臂 vs 裸三值臂」判别位 acc/连贯性差；用以**自证**「旋转是保能力关键」这一 vendor 论断，而非采信。
- 明确不做：27B 级训练/微调；27B 工件下载（超 RAM）；任何以「重训练」为名的算力承诺。

**D. 与我们已有真机证据的关系**：§3.1 的「PTQ 直接三值 = 乱码」与 vendor 的「无旋转运行时 = 静默劣化」**同向**；因此 C 的对照臂是本项目唯一能**独立**验证「旋转域三值」是否真有效的路径（不依赖厂商二进制）。
### 3.5 判别位 A/B：现役件 vs 原生三值件（R462 夹具 28 例 · ctx 1024）｜同窗真机 2026-09-21

**问题**：换 Bonsai 的「特殊 llama」（厂商 fork）后，模型能力在**同一夹具**上是否更好／不退化？三值件能否顶替现役判别位件？

**读数（同机同窗串行；原始 JSON = `/tmp/r462_out_<TAG>.json`，档案 = `docs/evidence/RF0006/probe-ab-r462.md`）**

| 臂 | 件 | 运行时 | 体积(B) | 占现役 | acc | 假跳 | 漏跳 | 未判定 | 壁钟(s) | 单例均(s) |
|---|---|---|---|---|---|---|---|---|---|---|
| `lfm3b-main` | LFM2.5-VL-3B-Q4_K_M | 主线 b11065（产品 pin） | 1,674,455,072 | 100.0% | **1.0000** | 0/14 | 0/14 | 0 | 869.4 | 31.1 |
| `lfm3b-fork` | LFM2.5-VL-3B-Q4_K_M | 厂商 fork prism-b10709 | 1,674,455,072 | 100.0% | **1.0000** | 0/14 | 0/14 | 0 | 482.6 | 17.2 |
| `bonsai8b-fork` | Ternary-Bonsai-8B-PQ2_0 | 厂商 fork prism-b10709 | 2,182,184,672 | 130.3% | **1.0000** | 0/14 | 0/14 | 0 | 2478.4 | 88.5 |
| `bonsai4b-fork` | Ternary-Bonsai-4B-PQ2_0 | 厂商 fork prism-b10709 | 1,074,969,344 | 64.2% | **0.5357** | 13/14 | 0/14 | 0 | 1000.4 | 35.7 |

**判读**

- 换运行时（同件）：`lfm3b-fork` 482.6s vs `lfm3b-main` 869.4s ⇒ **1.80× 提速**，能力三项逐位相同 ⇒ 运行时是**吞吐变量**、不是能力变量（回答「Bonsai 的特殊 llama 是否带来指数级/退化」：**否，线性且更快**，见 §7 QR1c 的 pp 标度读数）。
- 8B 三值件（130.3% 现役体积）：acc **1.0000** · 假跳 0/14 · 漏跳 0/14；单例 88.5s。
- 4B 三值件（64.2% 现役体积）：acc **0.5357** · 假跳 13/14 · 漏跳 0/14；单例 35.7s ⇒ QR2 主判据见 §4 判定列。
- **QR2 判定（预注册判据 = `acc 1.000 ∧ 假跳 0/14`）**：4B 档 = **不达标**（acc 0.5357 · 假跳 13/14）⇒ 路线 R1 **在 4B 档不可用**（恒判 S：14 例真实请求里 13 例被跳过）；8B 档达标但体积 = 现役 **130.3%** ⇒ 单看体积是净亏，只能按「能力/速度优先」另行取舍。
- 4B 假跳形态与历史低档一致（1.5B 档 13–14/14）：本夹具上小档三值件表现为**恒判 S**，非随机错。
- **天花板效应（诚实边界）**：现役 3B 已 `1.0000 / 0/14`，夹具无剩余分辨率（分辨率 1 例 = 1/14）⇒ 「8B 更好」在本夹具上**不可测**；要判「更好」须换**有分辨率**的靶（真实开发任务 × codex 同窗真值，即主线 DoD ①）。
- 本读数**不**覆盖：`ctx 1024`（产品档 4608）、多轮工具编排、生成类；无 GPU 主机；单跑一次（未重复测 ⇒ 不确定性 ≥1 例）。

## §4 四路线与判定
| 路线 | 内容 | 体积/内存（实测） | 状态 | 风险 |
|---|---|---|---|---|
| **R1 换原生三值件** | 用**原生三值训练**的 gguf 替换现役判别位件（唯一真三值可行路径） | `Ternary-Bonsai-4B-Q2_0_g64` **1,085.10 MiB = 现役 68.0%（达 §0 ①）**；峰值 RSS **1.27 GiB（−50%）**；**能力读数待 QR1b/QR2（须厂商 fork 运行时）** | **推荐 · 首选（体积达；能力待验）** | 能力须 QR2 真验；**须换 llama.cpp 运行时（厂商 fork）**；**速度 0.4 t/s**（壁钟风险）；产品 pin 待确认 |
| R2 混精 PTQ | 现有件：attn/embedding/output 保 Q4_K+，仅 FFN 三值（imatrix 只作用于 K 系） | 预期空间 **< Q2_K**（三值件本身即不可用 ⇒ 只能「少三值」） | 备选 | 文献 PTQ 三值要么需可学习调制（CAT-Q），要么旋转域格式（ITQ3_S）——llama.cpp 无此类型 |
| **R3 同族低比特（兜底）** | 不做三值，走 K 系低比特 | 现役件 Q2_K 投影 1,036.03 MiB（−35.1%）· Q3_K_M −18.9%；1.5B 件上 Q2_K/Q3_K_M **实测保能力** | 兜底 · **立即可用** | 现役件需另测判别位（1.5B 件的保能力不可外推） |
| R4 视觉塔 | 压 `mmproj` | **否决** | — | `ncols 4304` 非 64 整除 ⇒ 分块量化硬失败 |

**候选件清点（HF 镜像实测尺寸，2026-09-21）**：

| 候选 | 尺寸 | 占现役 | 备注 |
|---|---|---|---|
| `prism-ml/Ternary-Bonsai-4B-gguf :: Ternary-Bonsai-4B-Q2_0_g64.gguf` | 1,085.10 MiB | **68.0%** | mainline 兼容件；需 Q2_0 支持（b11065 已具） |
| `prism-ml/Ternary-Bonsai-4B-gguf :: …-Q2_0.gguf`（group-128）/ `…-PQ2_0.gguf` | 1,025.17 MiB | 64.2% | 打包非 g64 / 需厂商 fork ⇒ mainline 兼容性**待确认** |
| `prism-ml/Ternary-Bonsai-1.7B-gguf :: …1.7B-Q2_0_g64.gguf` | 467.46 MiB | 29.3% | <3B 档；按既有经验（1.5B 假跳 13–14/14）**预期不达判别位** |
| `prism-ml/Ternary-Bonsai-8B-gguf :: …8B-Q2_0_g64.gguf` | 2,203.11 MiB | 138.0% | 体积换能力；须过内存闸（MemTotal 3.57 GiB） |
| `microsoft/bitnet-b1.58-2B-4T-gguf :: ggml-model-i2_s.gguf` | 1,132.78 MiB | 70.9% | `i2_s` 系 BitNet 侧打包 ⇒ mainline 支持面**待确认**；且 2B < 3B 档 |

> 生产路径注记：上游三值件由 **F16 源 + 厂商量化器**产出（4B F16 7,676.99 MiB ⇒ 三值件 1,085.10 MiB），**不是**从已量化件二次量化 —— 与 §3.1 的 PTQ 失败同向，也解释了为何 R1 与 R2 的期望完全不同。

---

## §5 文献（只作机制假设，非结论）

| arXiv | 日期 | 机制要点（与本项目的关系） |
|---|---|---|
| 2602.07374 TernaryLM | 2026-02-07 | **原生**三值训练（1.58-bit），明言 PTQ 路线（量化预训练全精度模型）不足 ⇒ 支持 R1 |
| 2606.26650 CAT-Q | 2026-06-25 | PTQ 三值需 **learnable modulation + softened ternarization**（可学习参数 ⇒ 需训练数据/算力）⇒ R2 的代价上界 |
| 2606.13054 TWLA | 2026-06-11 | PTQ 三值权重 + 低比特激活；重尾激活分布是主障 ⇒ 与本机「三值即乱码」同向 |
| 2602.05269 HGF | 2026-02-07 | BitNet 式 1.58-bit 相对 FP16 **困惑度退化 20–25%**，需选择式低秩修正稳定 ⇒ 三值非免费 |
| 2603.27914 ITQ3_S | 2026-03-30 | 3-bit 需**旋转域（FWHT）平滑**压离群 ⇒ llama.cpp 无对应类型，R2 无现成落点 |

纪律：论文只提供机制假设；任何一条要算「已实施」，必须在本仓**真机单变量对照**改动 §0 判据（RF0005 §5 文献小步）。

---

## §6 预算 · 闸 · 可复跑绑定

- **磁盘**：下载 1,085 MiB（可选 8B 2,203 MiB）；现 free 9.6 G（本轮器具已占 `/tmp/llamatq` 3.9 G + `/tmp/probe` 532 M，可清）。
- **时间**：量化实测 1.1 GB / **16.7 s** ⇒ 4B 级 <2 min；生成 ~2.3 t/s（2 核）。
- **网络闸（实测）**：`huggingface.co` **HTTP 000（不可达）** · `hf-mirror.com` 200 · `modelscope` 302 · `github` 200 · `pypi` 200 ⇒ 下载**必须** `HF_ENDPOINT=https://hf-mirror.com`；HF 直连不可用不得当「候选不存在」。

- **GitHub release 通道（实测 2026-09-21）**：`github.com` 直连 **000（不可达）** ⇒ 用镜像 `https://gh-proxy.com/<原始URL>`（实测 17,108,139 B / **1.3 s**）；`api.github.com` 直连 **通**（release 资产清单可读）。
- **厂商运行时件（本条新增）**：`llama-prism-b10709-9a9394a-bin-ubuntu-x64.tar.gz` **17,108,139 B**（sha256 `48b487f00fd2b27bc3ef77c7…`，经 gh-proxy 取）；**frozen legacy 线** = `prism-b9601`（支持旧 `Q2_0` id42 打包）。
- **磁盘回收**：fork 加载旧打包时主线/分支产出的 49 MB 转轮日志已删，仅留 3.2 KB 切片（`/tmp/forkr/legacy_load_head.txt`）。
- **器具闸**：产品 `AGENTFRAMEWORK_LLAMA_BIN` 现盘未设 / `llama-server` 不在盘 ⇒ 判别位夹具复跑前须先钉本地 build（**待确认**，属阻断项）。
- **可复跑绑定**（三段式）：
  - 投影：`llama-quantize --dry-run --allow-requantize <src.gguf> <TYPE>`
  - 量化：`llama-quantize --allow-requantize <src.gguf> <out.gguf> <TYPE> 2`
  - 探针：`llama-cli -m <out.gguf> -st -p "<probe>" -n 16 --temp 0 -c 512 -t 2 --no-display-prompt`
  - 上游件：`releases/download/b11065/llama-b11065-bin-ubuntu-x64.tar.gz`（16.1 MB；sha256 见证据件）
- **红线遵从**：零 `src/` 改动 · 不新增夹具 · 不占主线轮 · 大产物留 `/tmp` 不入仓 · 提交逐名列名（禁 `git add -A`）。

---

## §7 排期（并行轨，不占主线轮次）

| 步 | 内容 | 出口（真机读数） | 状态 |
|---|---|---|---|
| QR1 | 下载 + 冒烟（**主线运行时**）**已完成 2026-09-21** | 1,137,806,656 B（逐字节 = 镜像 API 原值，本地 sha256 `9d968b04…ef0c`）· 峰值 RSS **1.27 GiB**（−50%）· 3/3 探针连贯（P2 `不成立` ✓ / P3 `The weather is great today.` ✓） | **部分 PASS（体积/内存）· 能力读数已降级**（vendor：主线缺 Hadamard 运行时 ⇒ `Q2_0` 静默劣化） |
| QR1b | **厂商 fork（`prism-b10709-9a9394a`）重跑冒烟，同件同 prompt 成对对照（fork vs mainline）** | fork 二进制可执行 ∧ 输出与主线**成对可比**；若 fork 输出亦不连贯 ⇒ 三值方向出局 | **PASS（2026-09-21 R609）**：fork 可执行 `rc=0` ∧ 3/3 探针连贯（P2 `不成立` ✓ / P3 `The weather is great today.` ✓ / P1 逐步展开被 `-n 32` 截断）。**诚实边界**：两侧在 P1–P3 上**皆连贯 ⇒ 该探针组无分辨力**，厂商所述「主线缺 Hadamard ⇒ `Q2_0` 静默劣化」**未被本探针证**；须换更强探针（多步算术终值 + QR2 判别位夹具 14 例） |
| QR1c | **厂商 fork × 新打包件（`Ternary-Bonsai-4B-PQ2_0.gguf` 1,074,969,344 B, 2.13 bpw group128）**：冒烟 + 速度/上下文标度实测 | 加载成功（`ftype: PQ2_0`）∧ 输出连贯 ∧ 给出**本机 fork 实测 pp/tg** 与 pp-vs-上下文曲线（回答「是否指数级」） | **PASS（2026-09-21 R609）**：`ftype: PQ2_0 - 2.13 bpw (group 128)` ✓ ∧ 输出连贯（含 `The capital of France is Paris.`）∧ 本机 **pp 5.2–6.3 t/s / tg 2.4 t/s** ∧ pp 标度 256→2048 **线性**（wall 56/95/178/369 s，边际 5.4–6.6 t/s ⇒ **非指数**）· 峰值 RSS **1.75–1.81 GiB 恒定**。器具事故（v1 REPL 空转 1.74 GB）与判据假阳性修正见 `docs/evidence/RF0006/ternary-recon-readings.md` §R10.1/10.5 |
| QR5 | **玩具级旋转对照臂**（≤0.3B，CPU 上自实现 blockwise Hadamard + g128 三值；对照「裸三值」） | 同体积下旋转臂 vs 裸三值臂的判别位 acc 差 > 0 ⇒ 独立自证「旋转域」机制（不依赖厂商二进制） | 未开（§3.4 C） |
| QR2 | 判别位夹具重跑（现役件 vs 4B 三值件，**须 fork 运行时**） | §0 ② 达（acc 1.000 ∧ 假跳 0/14）；**先算壁钟预算**：0.4 t/s ⇒ 14 例 × 2 臂 @ ~12 tok 已 ≥15 min 量级 | 未开（阻塞于 QR1b：运行时口径未定 ⇒ 先验运行时） |
| QR3 | R1 若不过 ⇒ R2 混精单变量（对照臂 = 同尺寸 Q2_K） | 增益 > Q2_K 才留 | 未开 |
| QR4 | 产品侧接线（本地推理 pin 换件 **+ 换运行时**） | **须用户放行** | 未开（**新增前置：运行时依赖，非仅换件**） |

**停机判据**：R1 在判别位判据上不达，且 R2 增益 < Q2_K ⇒ **停止三值方向**，落 R3，并把「三值对现有件不可用」写成结论（本轮已具 3.1 真机证据）。
