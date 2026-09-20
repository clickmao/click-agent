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
| 2 | 判别位能力 | `acc = 1.000` ∧ `假跳 0/14`（R577 判据，**不得放宽**） | 现役件 1.000 / 0/14；三值 PTQ 件 **探针全乱码** | **未达标** |
| 3 | 产品可加载 | 本地推理 pin 支持该 ggml 类型；AOT/零反射面不受影响 | 上游 b11065 具 Q2_0/Q1_0；产品 pin **待确认** | **待确认** |
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

**视觉塔不可压（硬失败）**：`mmproj`（Q8_0, 556.10 MiB）→ Q1_0 报 `v.blk.0.ffn_down.weight - ncols 4304`（非 64 整除）⇒ **556.10 MiB 为不可压底座**，压缩率上界由它约束。

---

## §4 四路线与判定

| 路线 | 内容 | 体积/内存（实测） | 状态 | 风险 |
|---|---|---|---|---|
| **R1 换原生三值件** | 用**原生三值训练**的 gguf 替换现役判别位件（唯一真三值可行路径） | `Ternary-Bonsai-4B-Q2_0_g64` **1,085.10 MiB = 现役 68.0%（达 §0 ①）**；**QR1 冒烟 3/3 连贯正确**、峰值 RSS **1.27 GiB** | **推荐 · 首选（QR1 PASS）** | 能力需 QR2 判别位真验；**速度 0.4 t/s**（壁钟风险）；产品 pin 待确认 |
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
| QR1 | ~~下载 + 冒烟~~ **已完成 2026-09-21** | 1,137,806,656 B（逐字节 = 镜像 API 原值，本地 sha256 `9d968b04…ef0c`）· **3/3 探针连贯**（P2 `不成立` ✓ / P3 `The weather is great today.` ✓）· 峰值 RSS **1.27 GiB**（−50%） | **PASS** |
| QR2 | 判别位夹具重跑（现役件 vs 4B 三值件） | §0 ② 达（acc 1.000 ∧ 假跳 0/14）；**先算壁钟预算**：0.4 t/s ⇒ 14 例 × 2 臂 @ ~12 tok 已 ≥15 min 量级 | 未开 |
| QR3 | R1 若不过 ⇒ R2 混精单变量（对照臂 = 同尺寸 Q2_K） | 增益 > Q2_K 才留 | 未开 |
| QR4 | 产品侧接线（本地推理 pin 换件） | **须用户放行** |

**停机判据**：R1 在判别位判据上不达，且 R2 增益 < Q2_K ⇒ **停止三值方向**，落 R3，并把「三值对现有件不可用」写成结论（本轮已具 3.1 真机证据）。
