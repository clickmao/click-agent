# RF0006 · QR2 原始读数 —— 判别位 A/B（R462 夹具 28 例 · ctx 1024 · 无 GPU）

> 本文件为 **新增** 读数档案（不改动 `ternary-recon-readings.md`，其 registry pin 保持 frozen）。
> 判读与决议见 `docs/plans/RF0006-ternary-gguf-compression.md` §3.5。

## 0. 可复跑绑定

- 运轮器：`eval/rf0006/qr2-ab/run-ab.sh`（sha256[:12] `502a2975fca8`）+ 说明 `eval/rf0006/qr2-ab/README.md`
- 夹具：`eval/rover/r462/bench_r462_w.py` + `eval/rover/r462/corpus-r462-w.json`（只读复用，未新增夹具）
- 夹具题集 sha256[:12]：`cd075177be5b`
- 固定参数（由 runner 给定）：`ctx=1024` `temp=0` `-t 2` `-np 1` `fa=off` `-b 512 -ub 512`，同机同窗串行（同一时刻一个 llama-server）

## 1. 臂汇总（逐臂原始 JSON）

| 臂 | 模型 | 运行时 | 结论 acc | 假跳 | 漏跳 | 未判定 | 生成 token 合计 | 壁钟(s) | 单例均(s) | 原始件 |
|---|---|---|---|---|---|---|---|---|---|---|
| `lfm3b-main` | LFM2.5-VL-3B-Q4_K_M | 主线 b11065（产品 pin） | **1.0000** | 0/14 | 0/14 | 0 | 56 | 869.4 | 31.1 | `/tmp/r462_out_lfm3b-main.json` sha12 `dd1c41b7880f` |
| `lfm3b-fork` | LFM2.5-VL-3B-Q4_K_M | 厂商 fork prism-b10709 | **1.0000** | 0/14 | 0/14 | 0 | 56 | 482.6 | 17.2 | `/tmp/r462_out_lfm3b-fork.json` sha12 `0dcb4b373b1c` |
| `bonsai8b-fork` | Ternary-Bonsai-8B-PQ2_0 | 厂商 fork prism-b10709 | **1.0000** | 0/14 | 0/14 | 0 | 56 | 2478.4 | 88.5 | `/tmp/r462_out_bonsai8b-fork.json` sha12 `c6be91c61380` |
| `bonsai4b-fork` | Ternary-Bonsai-4B-PQ2_0 | 厂商 fork prism-b10709 | **0.5357** | 13/14 | 0/14 | 0 | 56 | 1000.4 | 35.7 | `/tmp/r462_out_bonsai4b-fork.json` sha12 `5a80364a9a42` |

## 2. 逐例（对照：want=夹具期望 · got=模型判定）

| # | family | want | lfm3b-main got/ok | lfm3b-fork got/ok | bonsai8b-fork got/ok | bonsai4b-fork got/ok |
|---|---|---|---|---|---|---|
| 1 | ack | S | S/Y | S/Y | S/Y | S/Y |
| 2 | ack | S | S/Y | S/Y | S/Y | S/Y |
| 3 | ack | S | S/Y | S/Y | S/Y | S/Y |
| 4 | ack | S | S/Y | S/Y | S/Y | S/Y |
| 5 | ack | S | S/Y | S/Y | S/Y | S/Y |
| 6 | ack | S | S/Y | S/Y | S/Y | S/Y |
| 7 | ack | S | S/Y | S/Y | S/Y | S/Y |
| 8 | ack | S | S/Y | S/Y | S/Y | S/Y |
| 9 | ack | S | S/Y | S/Y | S/Y | S/Y |
| 10 | ack | S | S/Y | S/Y | S/Y | S/Y |
| 11 | ack | S | S/Y | S/Y | S/Y | S/Y |
| 12 | ack | S | S/Y | S/Y | S/Y | S/Y |
| 13 | ack | S | S/Y | S/Y | S/Y | S/Y |
| 14 | ack | S | S/Y | S/Y | S/Y | S/Y |
| 15 | real | P | P/Y | P/Y | P/Y | S/N |
| 16 | real | P | P/Y | P/Y | P/Y | S/N |
| 17 | real | P | P/Y | P/Y | P/Y | S/N |
| 18 | real | P | P/Y | P/Y | P/Y | S/N |
| 19 | real | P | P/Y | P/Y | P/Y | S/N |
| 20 | real | P | P/Y | P/Y | P/Y | P/Y |
| 21 | real | P | P/Y | P/Y | P/Y | S/N |
| 22 | real | P | P/Y | P/Y | P/Y | S/N |
| 23 | real | P | P/Y | P/Y | P/Y | S/N |
| 24 | real | P | P/Y | P/Y | P/Y | S/N |
| 25 | real | P | P/Y | P/Y | P/Y | S/N |
| 26 | real | P | P/Y | P/Y | P/Y | S/N |
| 27 | real | P | P/Y | P/Y | P/Y | S/N |
| 28 | real | P | P/Y | P/Y | P/Y | S/N |

## 3. 运行时/加载证据（逐字切片）

- 厂商 fork × `PQ2_0` 加载：`ftype: PQ2_0` · `modalities: text`（R609 同件切片）
- 主线 `b11065` × `PQ2_0`：**厂商逐字为拒载**（`Rejects PQ2_0/PTQ1_0 as unknown types`，见 §3.3 F.1）；本条**本窗未复测**，故不列入结论
- 旧打包 `Q2_0_g64` × 厂商 fork：可加载（`ftype: Q2_0`）但吞吐 0.2–0.3 t/s（≈新打包件 1/8）⇒ 不可用，非「拒载」

## 4. 结论（只由本窗读数支撑）

1. **同件换运行时**：同一 3B 件在 fork 上壁钟 482.6s vs 主线 869.4s ⇒ **1.80× 提速**，且两侧 `acc`/`假跳`/`漏跳` 逐位相同 ⇒ 运行时更换**不改变**判别位结论，只改吞吐。
2. **8B 三值件（130.3% 现役体积）**：acc **1.0000** · 假跳 0/14 · 漏跳 0/14 · 壁钟 2478.4s（88.5s/例）
3. **4B 三值件（64.2% 现役体积，= QR2 主判据）**：acc **0.5357** · 假跳 13/14 · 漏跳 0/14 · 壁钟 1000.4s

## 5. 读数背书

- 逐臂通过率：`lfm3b-main` 28/28 · `lfm3b-fork` 28/28 · `bonsai8b-fork` 28/28 · `bonsai4b-fork` 15/28（逐例见 §2）
- 形式门禁（改证据/登记表后必跑）：**14/14（Failed 0 · Passed 14 · Total 14 · 构建 0 error · TEST_RC=0）**（Debug 过滤集 `VerificationForm|SkillGeneralization|DevPlanDocRef`；本次构建 **0 error**）
- 判决件：本步骤零产品源码改动 ⇒ 无 AOT/单测等级主张；`src/` 净改动 0，`git diff --stat -- src/` 为空可复核。

## 6. 诚实边界

- **夹具天花板**：现役 3B 已 `acc 1.0000 ∧ 假跳 0/14`，夹具对本档**无剩余分辨率**（分辨率 = 1 例 = 1/14）⇒ 「8B 更好」在本夹具上**不可测**；本读数只支持「不劣化」，不支持「更好」。
- **上下文档不符产品**：本轮 `ctx=1024`，产品档 4608；长上下文下三值件行为未测。
- **单跑一次**：每臂 28 例单跑，未做 reps；不确定性 ≥1 例（1/14）。
- **无 GPU**：主机无 GPU，本轮只测推理正确性与壁钟，不测显存；「体积↓ ⇒ 显存↓」在 §3.3 用 Bonsai 家族公开读数论述，非本机实测。
- **只覆盖判别位一族**（ack 跳过 vs 真实请求 28 例）：不覆盖生成类、多轮工具编排、上下文精排，也不覆盖真实开发任务的质量。
- **运行时未复测主线拒载**：`PQ2_0` 在主线 `b11065` 上拒载系厂商逐字（§3.3 F.1），本窗未复测。
- **旧打包件读数归因**：旧 `Q2_0_g64` 在 fork 上可载但 0.2–0.3 t/s，属「加载不留警告但退化」，与本轮 `PQ2_0` 读数不可混用。

