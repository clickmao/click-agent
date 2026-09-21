# RF0006 原始读数（三值/低比特量化调研 · 2026-09-21）

> 本件是 `docs/plans/RF0006-ternary-gguf-compression.md` 的**原始读数档案**：命令逐条 + 输出逐字，**未加工**。
> 复跑环境：`~/AgentFramework` @ main；主机 `nproc=2` / `MemTotal 3,747,744 kB` / `MemAvailable 2,983,272 kB` / 磁盘 `50G 38G 9.6G 80%` / 无 GPU。

## R0 · 器具与来源 pin

```
$ cd /tmp && curl -sSL -o l.tar.gz \
  https://github.com/ggml-org/llama.cpp/releases/download/b11065/llama-b11065-bin-ubuntu-x64.tar.gz
$ ls -l l.tar.gz            → 16.1 MB
$ sha256sum l.tar.gz        → f00971c1b044fae179230bfc6f8d9f8461b778fef9ffac2b450088081a8ecd43
$ tar xzf l.tar.gz          → /tmp/llamatq/llama-b11065/{llama-cli,llama-quantize,llama-server,...}
```

`llama-quantize` 类型表（`--help` 逐字摘录）：
```
36 or TQ1_0  : 1.69 bpw ternarization
37 or TQ2_0  : 2.06 bpw ternarization
40 or Q1_0   : 1.125 bpw quantization
41 or Q2_0   : 2.25 bpw quantization (group 64)
1  or F16    : 16.00 bpw   ... (略)
19 or IQ1_S  : 1.56 bpw quantization
```
`--dry-run` 逐字：`calculate and show the final quantization size without performing quantization`
`--allow-requantize` 逐字：`allow to requantize a quantized model (WARNING: will severely reduce quality...)`
`usage:` 行逐字：`[--allow-requantize] [--leave-output-tensor] [--pure] [--imatrix] [--include-weights] [--exclude-weights] [--output-tensor-type] [--token-embedding-type] [--tensor-type] [--tensor-type-file]`

## R1 · 现有 gguf 清点（`find ~/.agentframework -name '*.gguf' -printf '%10s  %p'`）

| 字节 | MiB | 路径 |
|---|---|---|
| 1,674,455,072 | 1,596.88 | `~/.agentframework/models/lfm25vl3b/LFM2.5-VL-3B-Q4_K_M.gguf` |
| 1,117,320,800 | 1,065.56 | `~/.agentframework/models/r1-distill-qwen-1.5b-q4km.gguf` |
| 1,117,320,736 | 1,065.56 | `~/.agentframework/models/qwen2.5-1.5b-instruct-q4km.gguf` |
| 583,109,984 | 556.10 | `~/.agentframework/models/lfm25vl3b/mmproj-LFM2.5-VL-3B-Q8_0.gguf` |
| 26,472,640 | 25.25 | `~/.agentframework/models/bge-q8.gguf` |
| **4,518,679,232** | **4,309.35** | 合计 4.21 GiB |

## R2 · `--dry-run` 投影矩阵（零写入）

```
$ ./llama-quantize --dry-run --allow-requantize <model.gguf> <TYPE>
```
| 模型 | 原档 | Q1_0 | Q2_0 | TQ1_0 | TQ2_0 | Q2_K | Q3_K_M |
|---|---|---|---|---|---|---|---|
| LFM2.5-VL-3B | 1,596.88 MiB | 532.61 (−66.6%) | 859.14 (−46.2%) | 695.87 (−56.4%) | 804.71 (−49.6%) | 1,036.03 (−35.1%) | 1,295.67 (−18.9%) |
| qwen2.5-1.5B | 1,065.56 MiB | 390.13 (−63.4%) | 659.74 (−38.1%) | 571.88 (−46.3%) | 630.45 (−40.8%) | — | — |
| r1-distill-1.5B | 1,065.56 MiB | 390.13 | — | 571.88 | — | — | — |
| **mmproj（VL）** | 556.10 MiB | **失败** | — | — | — | — | — |
| bge-q8 | 25.25 MiB | 11.26 (3.99 BPW) | — | — | — | — | — |

mmproj 失败逐字：`v.blk.0.ffn_down.weight - ncols 4304` ⇒ 列数非 64 整除、分块量化硬失败。

## R3 · 真实量化 + 连贯性探针（qwen2.5-1.5B，源 = Q4_K_M 1,117,320,736 B）

```
$ time ./llama-quantize --allow-requantize <src> /tmp/llamatq/out/qwen15b-Q1_0.gguf Q1_0 2
→ real 0m16.7s   (Q1_0 落盘 415,033,888 B)
$ ./llama-cli -m <out.gguf> -st -p "<probe>" -n 16~20 --temp 0 -c 512 -t 2 --no-display-prompt
```
| 类型 | 落盘 | 占原档 | tool 报 (BPW) | P1「2+3*4=」 | P2「判断：'1 大于 2'」 | P3「中译英：今天天气很好」 |
|---|---|---|---|---|---|---|
| **Q4_K_M（原档）** | 1,117,320,736 B | 100% | — | `2 + 3 * 4 = 14` | `不成立。` | `The weather is very good today.` |
| Q3_K_M | 924,455,968 B | 82.7% | 875.96 MiB (4.13) | `2 + 3 * 4 = 14` | `不成立。` | — |
| Q2_K | 752,880,160 B | 67.4% | 712.33 MiB (3.36) | `2+3*4=2+12=14` | `不成立。` | — |
| TQ1_0 | 605,611,552 B | 54.2% | 571.88 MiB (2.70) | `ovidِTo年的 一闪声idorunger landak figureadhinuxurgeon statistics` | `ento�om applications digitindenewoodiniculp consc gıda>'.(us digit Ley` | — |
| TQ2_0 | 667,026,976 B | 59.7% | 630.45 MiB (2.98) | **与 TQ1_0 逐字相同** | **与 TQ1_0 逐字相同** | — |
| Q2_0 | 697,734,688 B | 62.4% | 659.74 MiB (3.11) | `共 viewed漆仅acie方才ike市长.getEnd host�除� sanity pur/owl pat` | `-sama�_STRUCTUREingurally�责任编辑 counted-osity bear credit-fe\- Pers \` | — |
| Q1_0 | 415,033,888 B | 37.1% | 390.13 MiB (1.84) | 乱码（同类） | — | — |

> 观察记录（**不归因**）：TQ1_0 与 TQ2_0 输出逐字相同，未做单变量分离。

## R4 · 通道连通性（`curl -o /dev/null -w '%{http_code}'`）

| 目标 | HTTP | 备注 |
|---|---|---|
| `huggingface.co` | **000** | 不可达（DNS 指向不可用地址） |
| `hf-mirror.com` | 200 | 160.16.86.14 ⇒ **下载走此** |
| `www.modelscope.cn` | 302 | 可用 |
| `github.com` | 200 | 上游件下载 OK |
| `pypi.org` | 200 | OK |

## R5 · 原生三值候选清点（经 hf-mirror API）

| 仓库 / 文件（API 原值） | 字节 | MiB | 占现役（1,596.88 MiB） | mainline 兼容 |
|---|---|---|---|---|
| `prism-ml/Ternary-Bonsai-4B-gguf :: Ternary-Bonsai-4B-Q2_0_g64.gguf` | 1,137,806,656 | 1,085.10 | **68.0%** | 是（Q2_0 = group 64） |
| `… :: Ternary-Bonsai-4B-Q2_0.gguf`（group-128） | 1,074,969,344 | 1,025.17 | 64.2% | **待确认**（非 g64 打包） |
| `… :: Ternary-Bonsai-4B-PQ2_0.gguf` | 1,074,969,344 | 1,025.17 | 64.2% | 需厂商 fork |
| `… :: Ternary-Bonsai-4B-F16.gguf`（源件） | 8,049,911,840 | 7,676.99 | 480.8% | — |
| `prism-ml/Ternary-Bonsai-1.7B-gguf :: …Q2_0_g64.gguf` | 490,163,968 | 467.46 | 29.3% | 是 |
| `prism-ml/Ternary-Bonsai-8B-gguf :: …Q2_0_g64.gguf` | 2,310,125,920 | 2,203.11 | 138.0% | 是 |
| `microsoft/bitnet-b1.58-2B-4T-gguf :: ggml-model-i2_s.gguf` | 1,187,801,280 | 1,132.78 | 70.9% | **待确认**（i2_s 打包） |

> 上游生产方式注记：三值件由 **F16 源 + 厂商量化器** 产出（4B F16 = 7,676.99 MiB ⇒ 三值 1,085.10 MiB），**不是** 从 Q4_K_M 二次量化得来 —— 与本轮 3.1 的 PTQ 失败同向。

## R6 · 本轮器具落点（临时件，不入仓）

`/tmp/llamatq/` 3.9 G（上游解包 + 6 件产物体）· `/tmp/probe/` 532 M（raw 探针输出）· 清理命令：`rm -rf /tmp/llamatq /tmp/probe`。

---

## R7 · QR1 冒烟：原生三值件 `Ternary-Bonsai-4B-Q2_0_g64`

```
$ curl -sSL -C - -o tb4b-Q2_0_g64.gguf \
    https://hf-mirror.com/prism-ml/Ternary-Bonsai-4B-gguf/resolve/main/Ternary-Bonsai-4B-Q2_0_g64.gguf
$ ls -l  → 1,137,806,656 B        # 与镜像 API 原值逐字节一致
$ sha256sum → 9d968b04a3c9a794897bcc744c8072fb6a061c0e42efd03c989401ddf8baef0c
              （镜像 API 未暴露 LFS sha256 ⇒ 上游摘要核对「待确认」；现有完整性证据 = 尺寸一致）
$ /usr/bin/time -v ./llama-cli -m tb4b-Q2_0_g64.gguf -st -p "<probe>" -n 24 --temp 0 -c 1024 -t 2 --no-display-prompt
```
| 探针 | 响应（逐字） | 判定 |
|---|---|---|
| P1「2+3*4=」n=24 | `Let's solve the expression step by step:` | 连贯（被 token 上限截断） |
| P1 加长 n=64 | `2 + 3 * 4` / `### Step 1: Follow the order of operations (PEMDAS/BODMAS)` / `- **P**arentheses - **E**xponents - **M**ultiplication and **D**iv` | **连贯、结构化**；n=64 内未收敛出终值 ⇒ **不主张「算对」** |
| P2「判断：'1 大于 2'」 | `不成立` | **正确** ✓ |
| P3「中译英：今天天气很好」 | `The weather is great today.` | **正确** ✓ |
| 峰值 RSS | 1,331,108 kB / 1,331,836 kB（两次运行）≈ **1.27 GiB** | 现役件记忆读数 ~2,643 MB ⇒ **−50%** |
| 速度 | `[ Prompt: 0.5 t/s | Generation: 0.4 t/s ]` | 同 build 1.5B-Q4_K_M 实测 2.3 t/s ⇒ **慢 ~5.7×** |

---

## §R8 体积 ⇒ 显存论原始读数（Bonsai 2 27B）｜用户令 2026-09-21

**取件（可复跑）**
- 模型卡 `https://hf-mirror.com/prism-ml/Ternary-Bonsai-2-27B-gguf/raw/main/README.md` — **22,785 B**，sha256[:16] **`cea1cb4770c21a6c`**
- 逐字节文件表 `https://hf-mirror.com/api/models/prism-ml/Ternary-Bonsai-2-27B-gguf/tree/main`（§8.1 由该 API 现取生成）
- 基座配置 `https://hf-mirror.com/Qwen/Qwen3.8-27B/raw/main/config.json` — sha256[:16] **`191e0af232104ed8`**
- 厂商 fork `https://github.com/PrismML-Eng/llama.cpp` release **`prism-b10709-9a9394a`**（2026-09-18）
- 命令：`export HF_ENDPOINT=https://hf-mirror.com`（**HF 直连不可达 000 ⇒ 必走镜像**）

### 8.1 仓库文件表（逐字节 = 镜像 API 原值）

| 文件 | 字节 | 体积 |
|---|---|---|
| `Ternary-Bonsai-2-27B-F16.gguf` | 53,808,408,928 | 50.11 GiB |
| `Ternary-Bonsai-2-27B-PQ2_0.gguf` | 7,206,168,928 | 6.71 GiB |
| `Ternary-Bonsai-2-27B-PTQ1_0.gguf` | 5,946,648,928 | 5.54 GiB |
| `Ternary-Bonsai-2-27B-mmproj-BF16.gguf` | 931,145,856 | 0.87 GiB |
| `Ternary-Bonsai-2-27B-mmproj-Q8_0.gguf` | 629,246,976 | 0.59 GiB |

### 8.2 README 逐字摘录（pinned sha 上，未改写）

```
## Model Overview

| Item              | Specification                                                                                    |
| :---------------- | :----------------------------------------------------------------------------------------------- |
| Base model        | Derived from Qwen3.8-27B, a 27B hybrid-attention causal language model (architecture unchanged)  |
| Parameters        | 27.36B total — 24.35B language backbone (64 blocks) + 2.54B embedding/LM head + 0.46B vision tower (27 blocks) |
| Architecture      | Hybrid attention (\~75% linear / \~25% full attention), SwiGLU MLP, RoPE, RMSNorm                   |
| Context length    | 262K tokens (inherited from the base model; kept practical on-device by the predominantly linear-attention backbone) |
| Weight format     | Ternary g128: {−1, 0, +1} weights with FP16 group-wise scaling, packed as **PTQ1_0** (dense trits) or **PQ2_0** (2-bit slots) |
| Weight basis      | Blockwise Hadamard rotation (block 1024, fixed ±1 signs) folded into the stored weights; the matching transform is applied to activations at runtime |
| Low-bit coverage  | Embeddings, attention projections, MLP projections, LM head                                       |
| Vision tower      | optional \~0.63 GB mmproj pack (Q8_0), loaded only for image input                                 |
| Deployed size     | **5.95 GB** (PTQ1_0) or **7.21 GB** (PQ2_0); 5.8 GB ideal at 1.72 bits/weight — see below           |
| Backends          | llama.cpp (CUDA, Metal, CPU)                                                                      |
| License           | Apache 2.0                                                                                        |
```
```
### Memory Requirement

| Format                          | True bits/weight | Size        | Reduction   |
| :------------------------------ | ---------------: | ----------: | ----------: |
| FP16 (baseline)                 | 16.0             | \~54 GB      | 1.0x        |
| Ternary g128 (ideal)            | 1.72             | 5.8 GB      | \~9.3x       |
| **GGUF PTQ1_0** (dense trits)   | **1.75**         | **5.95 GB** | **\~9.0x**   |
| **GGUF PQ2_0** (2-bit slots)    | **2.13**         | **7.21 GB** | **\~7.5x**   |

Practical deployment needs packing formats that efficient kernels can consume, and this repo ships two: **PTQ1_0** packs trits densely and lands essentially on the information-theoretic target, while **PQ2_0** stores each trit in a 2-bit slot, trading footprint for cheaper unpacking. Neither is uniformly faster — see the throughput table below for where each wins. These sizes describe the language model alone, the only component that must stay resident for text inference; 26.2M parameters (**0.0976%** of the language model — the recurrent state path of the linear-attention layers, plus the normalization weights) remain in higher precision and are counted in the 1.72 figure.

Unlike conventional low-bit builds — whose advertised labels understate their true average bit-width (a widely-used "2-bit" build of Qwen3.8-27B is really 2.8 bits/weight at 9.4 GB) — the Bonsai representation carries a bit-width that matches its name.
```
```
### These files need our llama.cpp build

The ternary hybrid-attention kernels live in the
[PrismML-Eng/llama.cpp](https://github.com/PrismML-Eng/llama.cpp) fork. **Stock llama.cpp will not
run these files.** It rejects `PQ2_0` and `PTQ1_0` as unknown types, and it loads `Q2_0` without any
warning and produces garbage, because it has no Hadamard activation runtime. Use a binary from the
fork.

```bash
```
```
## Cross-Platform Throughput

`tg128` is token-generation throughput over 128 generated tokens (the memory-bandwidth-bound, interactive phase); `pp512` is prompt-processing throughput over 512 input tokens (the compute-bound phase). Both in tokens/s, measured with `llama-bench` on these GGUF packs (custom low-bit kernels), at batch size 1 and depth 0 with no vision tower. NVIDIA energy is board power including HBM/GDDR.

| Platform                     | PQ2_0 TG128 | PQ2_0 PP512 | PQ2_0 J/tok | PTQ1_0 TG128 | PTQ1_0 PP512 | PTQ1_0 J/tok |
| :--------------------------- | ----------: | ----------: | ----------: | -----------: | -----------: | -----------: |
| RTX 5090 (32 GB)             | **129.9**   | 3893        | **1.95**    | 120.5        | 1805         | 2.15         |
| RTX PRO 6000 Blackwell       | 124.8       | **4020**    | 2.49        | 117.9        | 1972         | 2.77         |
| H100 SXM (80 GB)             | 113.9       | 2830        | 2.69        | 86.9         | 1237         | 3.18         |
| RTX 6000 Ada (48 GB)         | 82.8        | 2431        | 2.51        | **90.4**     | 1657         | 2.49         |
| RTX 4090 (24 GB)             | 81.2        | 3124        | 2.99        | **91.1**     | 1645         | 2.58         |
| L40S (48 GB)                 | 74.4        | 2868        | 3.24        | **81.8**     | 1543         | 2.82         |
| A100 SXM (80 GB)             | 73.9        | 1328        | 3.43        | 54.7         | 706          | 4.28         |
| L4 (24 GB, 72 W)             | 29.8        | 777         | 2.42        | **32.1**     | 467          | **2.25**     |
| Laptop (Apple M5 Pro, Metal) | 28.1        | 387         | —           | —            | —            | —            |

On the laptop the FP16 baseline (\~54 GB) does not fit at all — the meaningful statement is not a speedup ratio but that a 27B model runs interactively on an everyday laptop. The measured decode streams \~204 GB/s of weights on the M5 Pro, confirming the memory-bandwidth-dominated profile that the low-bit representation is built to exploit. The M5 Pro figure is measured on a quiet machine; this laptop swings \~4% with background load.

The two packings are a genuine trade rather than a strict ordering. PTQ1_0 moves 17% less weight data per step, but unpacking dense trits costs arithmetic, so it wins on the Ada-generation parts and the L4 — where memory is the binding constraint — and loses on H100, A100, and the Blackwell cards, where batch-1 decode is limited by instruction throughput and launch overhead instead. Prompt processing, being compute-bound, favors PQ2_0 everywhere.

The Apple row carries no per-token energy figure because the two platforms' instrumentation does not enclose the same components: `nvidia-smi` includes the card's HBM/GDDR, while Apple's `powermetrics` reports CPU, GPU, and ANE with no DRAM rail. What the measurement does support is absolute draw: the M5 Pro decodes at **27.5 W** on the GPU rail and 34.1 W across CPU and GPU, against 300–455 W of board power for the NVIDIA cards above.
```
```
## Intelligence Density

Intelligence density captures the ratio of a model's capability to its deployed size:

```
D = -log2(1 - score/100) / size_GB
```

| Variant                                  | Size (GB) | Benchmark avg | Intelligence Density (1/GB) |
| :--------------------------------------- | --------: | ------------: | --------------------------: |
| **Bonsai 2 27B**                         | **5.80**  | **84.78**     | **0.469**                   |
| Ternary Bonsai 27B (previous release)    | 5.75      | 80.98         | 0.416                       |
| Qwen3.8-27B IQ2_XXS                      | 9.4       | 72.59         | 0.199                       |
| Qwen3.8-27B UD-Q4_K_XL                   | 17.6      | 85.18         | 0.157                       |
| Qwen3.8-27B FP16                         | 54        | 86.32         | 0.053                       |

Bonsai 2 27B delivers over **2.3x** the density of the densest conventional build (IQ2_XXS at 0.199) and nearly **9x** FP16 — no conventional build of Qwen3.8-27B exceeds 0.2. Each stored gigabyte is translated into far more usable intelligence. Against the previous Bonsai 27B release, density rises from 0.416 to 0.469, a 12.5% gain; that row is recomputed on these same 14 benchmarks for a like-for-like comparison.
```
```
## Limitations

- **The quality–footprint trade-off**: the ternary model retains 98.2% of the full-precision average, and the gap is modest and predictable — the reasoning core (math, coding) stays within a few points of baseline, with the difference concentrated in the most demanding categories
- **Native low-bit kernels**: the dense PTQ1_0 packing (1.75 bits/weight, 5.95 GB) now exists, but unpacking trits costs arithmetic — it is faster on Ada-class and smaller accelerators and slower on Ampere, Hopper, and Blackwell, where batch-1 decode is not bandwidth-starved; returning the footprint advantage as latency on every target is an active engineering target
```
### 8.3 基座 `Qwen3.8-27B` 文本配置原值（config.json）

| 键 | 值 |
|---|---|
| `num_hidden_layers` | `64` |
| `full_attention_interval` | `4` |
| `num_attention_heads` | `24` |
| `num_key_value_heads` | `4` |
| `head_dim` | `256` |
| `hidden_size` | `5120` |
| `max_position_embeddings` | `262144` |
| `vocab_size` | `248320` |
| `tie_word_embeddings` | `false` |
| `linear_num_value_heads` | `48` |
| `linear_num_key_heads` | `16` |
| `linear_key_head_dim` | `128` |
| `linear_value_head_dim` | `128` |
| `linear_conv_kernel_dim` | `4` |

**派生**：层数 `64` = 全注意力 `64 / full_attention_interval(4)` = **16 层** + 线性注意力 **48 层**（与模型卡「~75% linear / ~25% full」一致）。

### 8.4 KV 预算推导（自算，公式留痕；**代读数 = 峰值 RSS / 权重字节，非 GPU 实测**）

KV 元素/token = 2 (K,V) × 16 全注意力层 × 4 KV heads × 256 head_dim = **32,768**

| 上下文 | KV fp16 (GB) | KV q8_0 (GB) | + 权重 PTQ1_0 (5.95 GB) | + 权重 PQ2_0 (7.21 GB) |
|---|---|---|---|---|
|   4,096 | 0.27 | 0.14 | 6.22 | 7.48 |
|  32,768 | 2.15 | 1.14 | 8.10 | 9.36 |
| 131,072 | 8.59 | 4.56 | 14.54 | 15.80 |
| 262,144 | 17.18 | 9.13 | 23.13 | 24.39 |

- 线性注意力层状态：`48 × linear_value_head_dim × linear_key_head_dim × 2 B` ⇒ 常数、**与上下文无关**（量级 ~10⁻¹ GB）⇒ 长上下文 KV 增量**全部来自 16 个全注意力层**。
- **未计入**：CUDA/驱动上下文 + 计算缓冲（~0.3–1.5 GB，随 batch/ubatch）；vision tower `mmproj-Q8_0` **629,246,976 B (0.59 GiB)** / BF16 **931,145,856 B (0.87 GiB)**（仅图像输入时驻留）。
- 本机**无 GPU** ⇒ 上表为**投影**；本机有效实测只有体积（逐字节）与峰值 RSS。

---

## §R9 「Bonsai 方案拆解 + 本地可行性」原始读数（用户令 2026-09-21）

**来源与 pin（本地副本 sha256 前 16 位）**

- 模型卡（Bonsai 2 27B） — https://hf-mirror.com/prism-ml/Ternary-Bonsai-2-27B-gguf/raw/main/README.md — `cea1cb4770c21a6c` (22785 B)
- 白皮书（Bonsai 2 27B） — https://raw.githubusercontent.com/PrismML-Eng/Bonsai-demo/main/bonsai-2-27b-whitepaper.pdf — `aea10331ede3b34c` (366237 B)
- 白皮书（Bonsai 27B v1） — https://raw.githubusercontent.com/PrismML-Eng/Bonsai-demo/main/bonsai-27b-whitepaper.pdf — `06451897df438a42` (418475 B)
- 白皮书（1-bit Bonsai 8B） — https://raw.githubusercontent.com/PrismML-Eng/Bonsai-demo/main/1-bit-bonsai-8b-whitepaper.pdf — `5ca2898214ccd1c3` (422015 B)
- 白皮书（Ternary Bonsai 8B） — https://raw.githubusercontent.com/PrismML-Eng/Bonsai-demo/main/ternary-bonsai-8b-whitepaper.pdf — `6c8be68c7a91840b` (363986 B)
- fork README（prism-b10709） — https://raw.githubusercontent.com/PrismML-Eng/llama.cpp/prism-b10709-9a9394a/README.md — `d3555efa0affedc2` (9071 B)
- 基座 config（Qwen3.8-27B） — https://hf-mirror.com/Qwen/Qwen3.8-27B/raw/main/config.json — `191e0af232104ed8` (4312 B)
- 模型卡（Ternary Bonsai 27B v1） — https://hf-mirror.com/prism-ml/Ternary-Bonsai-27B-gguf/raw/main/README.md — `435746555e2d153a` (23239 B)

### 9.1 fork README 逐字（`prism-b10709-9a9394a`，行号为本地副本）

10: > - `*-PQ2_0.gguf` (fork group-128, ggml id 142): preferred on Metal, CUDA, HIP and CPU. About 6% smaller than group-64.
11: > - `*-Q2_0_g64.gguf` / 27B `*-Q2_g64.gguf` (official group-64, ggml id 42): runs on every backend here AND on mainline llama.cpp. If unsure, use this. Newer model releases name this file plain `*-Q2_0.gguf`.
12: > - `*-Q2_0.gguf` on OLDER model repos is the **deprecated legacy format** (group 128 stored as id 42). It does not load on these builds; the error tells you which file to get instead. If you must run it, use the frozen [`prism-v5`](https:/

### 9.2 白皮书/模型卡 逐字关键句（本地副本行号）

**bonsai-2-27b**
  56: Bonsai 2 27B uses the same hybrid-attention architecture as Qwen3.8-27B [3]. Its matrix
  80: tation, while the MLX package retains it in full precision. Within the language model, 0.0976%
  92: Hybrid attention (∼75% linear attention / ∼25% full attention), SwiGLU MLP,
  95: 262K tokens (full-context capable, enabled by the predominantly linear-
  102: Blockwise Hadamard rotation (block 1024, fixed ±1 signs)
  104: Embeddings, attention and linear-attention projections, MLP projections, LM
  120: the figure tabulated over all language-model parameters in Table 3 is 1.72 bits per weight, a
  126: which constitutes only 0.0976% of the language model, or 52 MB at bf16. It moves the ternary
  127: model from 1.71 to 1.72 bits per weight.
  174: While the weights of Bonsai 2 27B can be represented using 1.72 bits per weight in princi-
  566: proaching the 1.72 bits per weight limit possible for the chosen ternary format. PQ2_0 uses
  577: Rotation overhead. At batch size 1 the activation-side rotation transform remains one of the
  591: The Hadamard- Welsh transform is O(n log n) in the activation
**bonsai-27b-v1**
  120: inference practical. We ship it with a full 262K-token context, enabled on edge devices via
  133: retains that intelligence rather than trading it away. Built on proprietary Caltech intellectual
  137: • Ternary Bonsai 27B — 80.49 average benchmark score (95% of FP16) at 1.71 bits per
  219: bit successor [5, 6] — avoids the quality collapse only by pretraining the network from scratch
  227: takes the opposite path from BitNet: it starts from an off-the-shelf pretrained model and moves
  300: matrix-heavy components — embeddings, attention projections, MLP projections, and the LM
  301: head — at a true 1.125 and 1.71 bits per weight. The other modality is handled separately and
  317: the shipped 262K-token context remains practical for full-context, on-device use, where a
  329: Hybrid attention (∼75% linear attention / ∼25% full attention), SwiGLU MLP,
  332: 262K tokens (full-context capable;
  338: Embeddings, attention projections, MLP projections, LM head
  354: an idealized raw-weight reduction of 16/1.71 ≈9.4× relative to FP16, before container over-
  1048: 262K-token context available for long-document analysis, full-repository code work, and other
  1142: benchmarks additionally raise the served context window — up to the model’s full 262K native window —
**1bit-8b**
  109: model built for real deployment, with 1-bit precision applied across embeddings, attention lay-
  201: This foundation comes from proprietary Caltech intellectual property that addresses a long-
  207: 1-bit weight precision across the full network: embeddings, attention layers, MLP layers, and
  251: GQA [2] (32 query / 8 KV heads), SwiGLU [34] MLP, RoPE [33], RMSNorm [32]
  257: Embeddings, Attention projections, MLP projections, and LM head
  280: cluding embeddings, attention projections, MLP projections, and the LM head. Normalization
**Ternary-Bonsai-27B 模型卡**
  46: - **Ships with a DSpark speculative-decoding drafter layer** trained against the Bonsai 27B target — a lossless **1.34x** decode speedup on the CUDA serving path
  61: | Base model        | Derived from Qwen3.6-27B, a 27B hybrid-attention causal language model (architecture unchanged)  |
  70: | Acceleration      | DSpark speculative-decoding drafter layer provided                                                |
  98: | DSpark drafter | Q4_1 (default)                     | 1.95 GB  | optional — speculative decoding     |
  99: | DSpark drafter | bf16 (reference)                   | 7.29 GB  | optional                            |
  203: ## Speculative Decoding: DSpark
  205: Ternary Bonsai 27B ships with a **DSpark** drafter layer trained against the low-bit target — a semi-autoregressive drafter with confidence-scheduled verification. Speculative decoding is lossless: verification preserves the targe
  207: The drafter is a compact **six-layer block-parallel transformer** conditioned on hidden states tapped from five evenly spaced layers of the target; its drafter-unique weights add roughly **0.5 GB at serving precision** (embeddings
  301: - **Does not fit a phone**: at \~7.2 GB the ternary build exceeds the \~6 GB per-app iOS memory budget; use the 1-bit companion via [MLX Swift](https://huggingface.co/prism-ml/Bonsai-27B-mlx-1bit) for phone deployment
  302: - **Served in 2-bit slots today**: the deployed footprint (\~7.2 GB) sits above the representation's \~5.9 GB native target; native ternary kernels are an active engineering target and would return the remaining bandwidth and foot
  306: ## Citation
  312: title   = {Bonsai 27B: Full 27B-Class Reasoning in Binary and Ternary

### 9.3 Bonsai-demo `scripts/` 清单（GitHub API，2026-09-21）

bonsai2-runtime.sha256, build_cpu_linux.sh, build_cuda_linux.sh, build_cuda_windows.ps1, build_mac.sh, common.sh, download_binaries.sh, download_models.sh, fetch_gguf.sh, make_kv_bias.sh, mlx_generate.py, mlx_generate_bonsai2.py, run_llama.ps1, run_llama.sh, run_mlx.sh, start_llama_server.ps1, start_llama_server.sh, start_mlx_server.sh, start_openwebui.sh, webui-config.json
⇒ **无权重转换 / 训练脚本**（build_* / download_* / fetch_gguf / run_* / start_*server / mlx_generate* / make_kv_bias）

### 9.4 本机规格（同窗实测）

- nproc=2（avx512）· MemTotal=3747744 kB · GPU=无 · 磁盘 `/` free=7.4G · HF 直连=000（须 hf-mirror）· github release 直连=000（须 gh-proxy 镜像）



## §R10 QR1c（P2_0 新打包件 × 厂商 fork `prism-b10709`，CPU）｜R609

### 10.1 首跑事故：器具失控放大 1,744,793,711 B（v1 → v2 修正）

- **现象**：`/tmp/forkr/tg128.txt` 自 08:19 起至 **08:26:52** 写出 **1,744,793,711 B / 581,597,563 行**；尾字节为无限 `> ` 提示符回显；`/` free 一度 4.8 GB（90% used）。
- **根因（同一命令行自证，两条并存）**：① v1 器具 `/tmp/forkrun.sh` 第 33/44 行**未传 `-st`** ⇒ 进交互 REPL；② `timeout 500` **只限时长不限写盘量** ⇒ stdin EOF 后空转刷提示符、无上限写盘。
- **定性**：**器具缺陷（测量层）**，非被测件缺陷；该臂读数判 `LOG_OVERFLOW` 不入对账（截断/溢出的证据不是证据）。v1 已得的 P1/P2/P3 冒烟件各 ~1.2 KB（normal 形态）**不受影响**，保留为有效读数。
- **处置**：删除溢出件（释放 1.7 GB，free 回到 5.4 GB）；v2 器具 `/tmp/forkrun2.sh`（sha256 见 10.4）四件：①每档 `head -c 4 MiB` **物理上限**；②全档补 `-st`；③起手/逐步 `df` 前置闸（<2000 MB 判 `ABORT_DISK`）；④模式检测（命中 `available commands:` 判 `REPL_INVALID`，不入对账）＋按 pid 采样 RSS（禁 `pkill -f`，同族自杀坑）。
- **同族先例**：本仓 2026-09 已有一次同型事故（REPL 空转 30 min 写 6.7 GB），器具修法一致；本次为**同族二次复现**，且新形态为「stage 级遗漏 `-st`」而非整脚本缺失 ⇒ 修正落到**逐档参数**而非脚本级开关。

### 10.2 v1 冒烟读数（有效，保留）——同件同探针，与 QR1 主文件读数并列

| 探针 | 输入 | fork(b10709) 输出 | 判定 |
|---|---|---|---|
| P1 | `2+3*4=` | 逐步展开（`Let's solve … Step 1: Follow the order of operations (` 后止） | 连贯；截断由 `-n 32` 预算所致，非畸形 |
| P2 | 判断「1 大于 2」只答成立/不成立 | `不成立` | 正确 |
| P3 | 中译英：今天天气很好。 | `The weather is great today.` | 正确 |
| S0 | legacy 件 `tb4b-Q2_0_g64.gguf` 在 fork 上加载 | 日志仅取 head 3.2 KB：**无 error/unknown/unsupported/deprecated 行**且出现 REPL 提示符 | **未取到拒载判定行 ⇒ 该项判「未测到」**，须以 `-st` 有界重跑（见 10.5 下一步） |
- 速度（v1 三探针同档）：prompt 5.3–5.8 t/s · generation 1.2–1.6 t/s（同窗与 QR1 主件 `0.4 t/s` 不同档，**不可相减，只并列**）。

### 10.3 起手闸（R609）

`roundcheck preflight --round R609`：FAIL=0 WARN=1 rc=0（P1 key ✓ 35 字符 · P2 权重 5 个 ✓ · P3 MemAvailable=647 MB（闸 400）· P4 free=5 GB · **P5 在飞执行体 `llama-server(pid=2282237)` = 兄弟会话的判别位臂（LFM2.5-VL-3B）⇒ 按并发纪律让行/勿写，本轨不触碰** · P6 轮号未占 · P7 R609 空闲 · P8 PUSH_PAUSED=yes）。

### 10.4 v2 有界读数（rc 全 0；同件同档串行，`-t 2`，CPU）

器具 `/tmp/forkrun2.sh`（v2）；件 = `/tmp/llamatq/out/Ternary-Bonsai-4B-PQ2_0.gguf` **1,074,969,344 B**；运行窗口 08:28:50 → 08:40:47。

| 档 | wall | 日志字节 | 峰值 RSS | 自报 `[ Prompt \| Generation ]` |
|---|---|---|---|---|---|
| tg128（深度 0 连贯探针） | 18 s | 1,209 | 1,640 MB | 5.2 t/s \| **2.4 t/s** |
| pp256 | 56 s | 1,701 | 1,814 MB | 6.3 t/s \| 0.0 |
| pp512 | 95 s | 1,677 | 1,753 MB | 6.0 t/s \| 0.0 |
| pp1024 | 178 s | 1,717 | 1,812 MB | 6.0 t/s \| 0.0 |
| pp2048 | 369 s | 1,685 | 1,812 MB | 5.5 t/s \| 0.0 |

- **pp-vs-上下文曲线 = 线性（回答「是否指数级」：否）**：wall 差商 `95−56=39 s/256 tok ⇒ 6.56 t/s`、`178−95=83 s/512 ⇒ 6.17 t/s`、`369−178=191 s/1024 ⇒ 5.36 t/s`，即 **边际 5.4–6.6 t/s 与自报值同量级（差 ≤20%）**——**两处独立读数一致**（外部墙钟差商 vs 引擎自报）。
- **峰值 RSS 与上下文无关**（1.75–1.81 GiB，256→2048 无增长）；tg 档生成 2.4 t/s（`The capital of France is` → **`The capital of France is Paris.`** 连贯；`-n 128` 未用尽 = EOS 早停，**该档不作吞吐读数**，只作连贯性读数）。
- **与 QR1（R7）并列、禁相减**：QR1 组合（**主线二进制 × legacy 打包件**）= prompt 0.5 / gen 0.4 t/s、RSS 1.27 GiB；QR1c 组合（**fork × PQ2_0 新打包件**）= prompt 5.2–6.3 / gen 2.4 t/s、RSS 1.8 GiB。两个因子（**打包件 + 运行时**）**同时改变** ⇒ 单变量不成立，差值**不得归因到任一件**；只报「组合读数」。

### 10.5 器具判据的首次假阳性（v2 `mode=REPL_INVALID` 5/5）与修正

- **现象**：v2 五档全判 `mode=REPL_INVALID`（判据 = 日志命中 `available commands:`）。但五档 `rc=0`、`wall` 远小于 `timeout 900`、日志 1.2–1.7 KB ⇒ 形态与「失控空转」相反。
- **根因**：该 build **单轮模式（`-st`）下也打印 `available commands:` 横幅** ⇒ 判据**绑了词面出现、未绑失控语义**（与「拒绝类规则判据：出现 ≠ 误用」同族）。
- **修正判据（失控语义三选一）**：①日志字节 ≥ 物理上限 `4 MiB`；②尾部出现 **≥20 连续 `> `** 提示符回显；③`rc=124`（超时）。
- **零重测复算（同日志）**：v1 溢出件（1,744,793,711 B ∧ 尾部连续 `> `）⇒ **判红** ✓；v2 五档（最大 1,701 B ∧ 无连续提示符 ∧ rc=0）⇒ **判绿** ✓。两侧样例齐备 ⇒ 修正后的判具有牙。
- **判据修正不入读数**：v2 的 `mode` 字段按修正判据**复算**，原标签作废并留痕（本条）；`rc`/`wall`/`RSS`/`tps` 读数不受影响（它们不依赖该字段）。

### 10.6 附加对照：「fork 拒载旧打包件」的推测被证伪

`prism-b10709` × legacy 件 `tb4b-Q2_0_g64.gguf`（`-st` 有界）：**加载成功**（`ftype : Q2_0`，22 行、920 B 日志，**无 error/unknown/unsupported/invalid 行**）⇒ v1 假定的「预期拒载」**不成立**。**边界**：本读数只证 fork 侧接受旧打包件；vendor 所述「**stock** 对 `PQ2_0`/`PTQ1_0` 报 unknown type」为**厂商文档采信**，本机未做 stock×PQ2_0 对照（若需，属独立单变量轮）。

### 10.7 本轨结论与诚实边界

- QR1b / QR1c 出口四合一（加载 `ftype: PQ2_0` ✓ ∧ 输出连贯 ✓ ∧ pp/tg 实测 ✓ ∧ pp-vs-上下文线性 ✓）**全部满足**，rc=0。
- **未测到/未做**：① 4096/8192 档（预算与兄弟臂内存占用下未跑，**不外推**）；② 判别位夹具 14 例（QR2，仍阻塞于运行时口径）；③ stock×PQ2_0 本机对照；④ 探针组（P1–P3）对「主线静默劣化」**无分辨力**（两侧皆连贯）——该结论仍只由厂商文档支撑。
- **器具面**：本轨首次真机跑即暴露一例**失控放大**（1.74 GB，测量层缺陷）与一例**假阳性判据**，两处均已在 v2 器具/判据中修正并留两侧样例（§10.1、§10.5）。
