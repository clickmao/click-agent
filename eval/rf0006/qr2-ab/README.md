# RF0006 · QR2 —— 判别位 A/B 运轮器（体积↔能力同一夹具对照）

目的：在**同一夹具、同一主机、同一窗**下比较「现役判别位件」与「原生三值件」的判别位能力，
给 RF0006 §0 判据（`acc 1.000 ∧ 假跳 0/14`）一个可复跑读数；顺带给出**同件换运行时**（主线 ↔ 厂商 fork）
的吞吐差，用来分开「模型换了」与「运行时换了」两个变量。

## 夹具（只读复用，未新增）
- `eval/rover/r462/bench_r462_w.py`（runner）+ `eval/rover/r462/corpus-r462-w.json`（28 例：14 正 S / 14 负 P）
- 运行参数由 `bench_r462_w.py` 固定：`ctx=1024`、`temp=0`、`-t 2`、无 GPU、`-np 1`、`fa=off`、`-b 512 -ub 512`

## 臂（4 条，逐臂一条命令，同一时刻只允许一个 llama-server）
| TAG | 模型 | 运行时 | 命令 |
|---|---|---|---|
| `lfm3b-main` | LFM2.5-VL-3B-Q4_K_M | 主线 `b11065` | `TAG=lfm3b-main BIN=/tmp/llamatq/llama-b11065/llama-server MODEL=$HOME/.agentframework/models/lfm25vl3b/LFM2.5-VL-3B-Q4_K_M.gguf PORT=48791 bash run-ab.sh` |
| `lfm3b-fork` | 同左 | 厂商 fork `prism-b10709` | 同上，`TAG=lfm3b-fork` / `PORT=48792` |
| `bonsai8b-fork` | `Ternary-Bonsai-8B-PQ2_0` | 厂商 fork | 同上，`MODEL=/tmp/llamatq/out/Ternary-Bonsai-8B-PQ2_0.gguf` / `PORT=48793` |
| `bonsai4b-fork` | `Ternary-Bonsai-4B-PQ2_0` | 厂商 fork | 同上，`MODEL=/tmp/llamatq/out/Ternary-Bonsai-4B-PQ2_0.gguf` / `PORT=48794` |

## 件（sha256 前 24 位；体积为逐字节）
| 件 | 体积(B) | sha256[:24] | 来源 |
|---|---|---|---|
| `LFM2.5-VL-3B-Q4_K_M.gguf` | 1,674,455,072 | `2436cf4bbac9a16e5dfc7799` | 本地产品 pin（R577 选型） |
| `Ternary-Bonsai-4B-PQ2_0.gguf` | 1,074,969,344 | `829abec7eb92f5bf464762be` | `prism-ml/Ternary-Bonsai-4B-gguf`（hf-mirror） |
| `Ternary-Bonsai-8B-PQ2_0.gguf` | 2,182,184,672 | `1376f942aa90e60f7b570c1d` | `prism-ml/Ternary-Bonsai-8B-gguf`（hf-mirror） |
| 厂商 fork `llama-server` | — | `e5c4211999de5b789b980626` | `PrismML-Eng/llama.cpp` release `prism-b10709-9a9394a`（x64 CPU 包 17,108,139 B / sha256[:16] `48b487f00fd2b27bc3ef77c7`） |
| 主线 `llama-server` | — | `99dfa7a3e8ab4d90a8341edd` | `ggml-org/llama.cpp` `b11065` |

## 产物
`/tmp/r462_out_<TAG>.json`：`acc / false_skip_n / miss_skip_n / undecided_n / gen_truth_sum / elapsed_s / rows[]`
（逐例 `i/src/turn/family/want/got/ok/render_len/render_sha16`）。汇总与判读见
`docs/evidence/RF0006/probe-ab-r462.md` 与 `docs/plans/RF0006-ternary-gguf-compression.md` §3.5。
