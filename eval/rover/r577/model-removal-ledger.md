# R577 · 本地判别权重置换台账（用户令「用r1 删3b」）

日期: 2026-09-19 ｜ 触发: 用户逐字「用r1 删3b」（推翻 R463 的 3B 选型）

## 一、换入（KEEP）

| 文件 | bytes | sha256[:32] | 来源 | 同源校验 |
|---|---|---|---|---|
| `~/.agentframework/models/r1-distill-qwen-1.5b-q4km.gguf` | 1,117,320,800 | `1741e5b2d062b07acf048bf0d2c514da` | hf-mirror `bartowski/DeepSeek-R1-Distill-Qwen-1.5B-GGUF` → `…Q4_K_M.gguf` | 与 R463 删除台账**尺寸逐字节相同 + sha256 同值** ⇒ 同源权重（不是"同名新文件"） |

> 注：unsloth 同款的 `…Q4_K_M.gguf` = 1,117,321,312 B（= 台账 +512 B）⇒ **不同源**，未采用。

## 二、换出（DELETE，用户令）

| 文件 | bytes | sha256 |
|---|---|---|
| `~/.agentframework/models/qwen2.5-3b-instruct-q4km.gguf` | 2,104,932,768 | `626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d` |

删除前核对 = R463 采用档（`config/base/models.yaml` 注释 + `registry r463.local-gate-model-switch` 记 `626b4a66…` 同值）。
删除后：本地判别通道**无回退档**。若 r1 判错，仅存守卫 = `skip_rejected_nonack`（R452 机械守卫）+ 未判定降级远端（`TurnGateJudge.Parse` → Pass）。

## 三、未动（避免越权扩删）

- `bge-q8.gguf`（26,472,640 B，embedder，非判别位）
- `lfm25vl3b/`（全仓 `config/`+`src/` grep **零引用**；同名 3B 级但非判别的 3B ⇒ **未删**，待裁定）

## 四、交付口径（诚实声明）

本次置换 = **F2 回退**（回到 R462-W 已测不合格档），**不是升级**。R462-W 原读数：`acc 0.500 / 假跳 14/14 / gen 157.8 tok 每次 / 17.5 s 每次`。
R577 用**同一语料（28 条产品实发 prompt）+ 同一器具（`eval/rover/r462/bench_r462_w.py`）+ 同一权重 sha**复算，读数落 `eval/rover/r577/arm-r1-requal.json`。
器具前置闸：`eval/rover/r462/selftest_r462_w.py` ⇒ 语料 vs 产品 dump **28/28 逐位命中** ⇒ SELFTEST PASS（起臂前已过）。

## 五、复现命令

```
# 权重（按 sha 校验同源）
sha256sum ~/.agentframework/models/r1-distill-qwen-1.5b-q4km.gguf | cut -c1-32   # 1741e5b2d062b07acf048bf0d2c514da
# 器具前置闸
python3 eval/rover/r462/selftest_r462_w.py                                      # 需 28/28 + SELFTEST PASS
# 复算
python3 eval/rover/r462/bench_r462_w.py --model ~/.agentframework/models/r1-distill-qwen-1.5b-q4km.gguf \
        --tag r577-r1-requal --port 48790 --ctx 1024 --out eval/rover/r577/arm-r1-requal.json
```
