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
