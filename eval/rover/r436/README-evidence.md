# R436 证据包 — 端到端 BRJ 网格（承重: 用户一轮任务总 API token 降幅）

- 轮次 **R436**｜HEAD `0fa24d7f7b49`｜二进制 sha256 `45c37dd5b88ffcf21041065c35a5d9190061927a5fda253c3710e682cfd8f3ba`（15188768 bytes, NativeAOT）
- 发布台账: /tmp/pub_r436.log；IL 警告 **0**；形态闸 True
- 判据预注册: `docs/plans/v0.57.0-r436-e2e-brj-token-kpi.md` §2–§5（读取数前写定）

## 1. 形态（C1）

| 项 | 读数 |
|---|---|
| il_warnings | 0 |
| native_code | True |
| publish_rc | 0 |
| env_i_version_rc | 0 |
| v0_raw_native_ok | True |
| v0_negative_control_rc | 131 |
| bin_bytes | 15188768 |
| C1 判定 | **PASS** |

## 2. 臂矩阵（p12, 12 轮; p8, 9 轮）

### p12

| 臂 | 远端调用 (G/J) | 远端 token (G/J) | 相对 A 降幅 | FN | FP | 门准确率 | 本地判官次 | r1 跳过轮 |
|---|---|---|---|---|---|---|---|---|
| A | 11 (11/0) | 27654 (27654/0) | 0.0% | 0 | 4 | 0.636 | 0 | 0 |
| B | 14 (7/7) | 20633 (19550/1083) | 25.39% | 0 | 0 | 1.000 | 0 | 4 |
| BRJ | 7 (7/0) | 19557 (19557/0) | 29.28% | 0 | 0 | 1.000 | 7 | 4 |
| BRJ2 | 7 (7/0) | 19564 (19564/0) | 29.25% | 0 | 0 | 1.000 | 7 | 4 |
| BP | 18 (11/7) | 29569 (28495/1074) | -6.92% | 0 | 4 | 0.636 | 0 | 0 |

### p8

| 臂 | 远端调用 (G/J) | 远端 token (G/J) | 相对 A 降幅 | FN | FP | 门准确率 | 本地判官次 | r1 跳过轮 |
|---|---|---|---|---|---|---|---|---|
| A | 8 (8/0) | 18481 (18481/0) | 0.0% | 0 | 3 | 0.625 | 0 | 0 |
| B | 11 (5/6) | 12884 (11962/922) | 30.29% | 0 | 0 | 1.000 | 0 | 3 |
| BRJ | 6 (5/1) | 12122 (11967/155) | 34.41% | 0 | 0 | 1.000 | 5 | 3 |

## 3. 判据 C1–C8

- **C1_形态** ✅ `{"il_warnings": 0, "native_code": true, "publish_rc": "0", "env_i_version_rc": 0, "v0_gate_pass": true, "v0_raw_native_ok": true, "v0_negative_control_rc": 131, "bin_sha256": "45c37dd5b88ffcf21041065c35a5d9190061927a5fda253c3710e682cfd8f3ba", "bin_bytes": 15188768, "head": "0fa24d7f7b499d5bdb29fb235df76f3759eb9361", "ok": true}`
- **C2_双源一致** — `{"all_S1_ok": true, "all_S2_delta0": true, "all_unassigned0": true}`
- **C3_门质量** ✅ `{"BRJ_p12_acc": 1.0, "BRJ_p12_fn_fp": [0, 0], "ok": true}`
- **C4_主KPI_token降幅** — `{"p12_BRJ_drop_pct": 29.28, "p12_target": 30.0, "p12_ok": false, "p8_BRJ_drop_pct": 34.41, "p8_ok": true}`
- **C4b_降幅分解** — `{"门_节省token": 7021, "门_占比pct": 25.39, "J本地化_节省token": 1083, "J本地化_占比pct": 3.92, "J本地化_远端请求消除数": 7}`
- **C5_单变量_J本地化** ✅ `{"B_J_calls": 7, "BRJ_J_calls": 0, "BRJ_judge_local_n": 7, "ok": true}`
- **C6_负控_无设备** ✅ `{"BP_r1_skips": 0, "BP_J_remote_calls": 7, "BP_remote_fallback_n": 7, "BP_drop_pct": -6.92, "ok": true}`
- **C7_确定性** ✅ `{"BRJ_tokens": 19557, "BRJ2_tokens": 19564, "delta_tokens": 7, "same_actual": true, "gate_r1_n": 8, "ok": true}`
- **C8_挂载生效** ✅ `{"gate_prompt_len_min": 452, "gate_prompt_len_max": 458, "growth_chars_seen": [70, 71], "role_seed_chars_seen": [78], "n_r1_records": 8, "ok": true}`

## 4. 降幅因果分解（p12）

- 门（跳过 4 个 ack 轮）: −7021 token = 相对 A 的 **25.39%**
- J 本地化: −1083 token = 相对 A 的 **3.92%**，并消除 **7 次远端 API 请求**
- 合计（BRJ vs A）: **29.28%**（目标 30.0% ⇒ **未达标**）
- p8 网格（任务构成不同）: **34.41%** ⇒ 达标

## 5. 诚实边界

- 远端读数为**桩**(OpenAI 兼容假 API)侧落盘的 `prompt_tokens_est/completion_tokens_est`：口径同上版（R434）可比，但非真实计费 token；真机远端（DeepSeek）自重放未做。
- 本地 r1 侧：判官 7 次共 1301 生成 token、墙钟 139s（串行, -np1, 本地 0 API 花费）；这些**不计入**上面的 API token 统计。
- 未测: 真机远端模型重放、并发多用户、AOT 二进制跨发布可复现性（本轮实测两次同源发布的 AOT 有 325 字节差异 ⇒ 二进制 sha 不能当源状态指纹）。

