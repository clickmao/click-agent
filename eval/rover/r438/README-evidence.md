# R438 证据 — 本地消化轮不得回放「从未发出的」内联块（缺陷修复）

**一句话因果链**：`IndustrialAgentV2.cs:1267` 在**门判定之前**无条件把「含本轮内联块」的用户消息写进 `message.SentContent`
→ 门判 `Skip` 的轮次**一次远端调用都没有**（块从未离开本机），但 `GetConversationHistoryAsync:2670` 按 `SentContent ?? Content`
把它落进会话历史 → 此后**每一次**远端调用都逐字回放这些从未发出的块 = 白付账。
修复：本地消化轮把 `SentContent` 归位为 `outboundText`（与首轮同形）。

## 1. 判据表（`verify_r438.py`，独立于 settle 的第二套实现；跑测落盘 `verify-r438.json`）

| 编号 | 判据 | 结果 |
|---|---|---|
| C2 | **臂 A 不变性**（关闸路径逐字节不受影响） | PASS 27654 vs 27654；逐调用 est 完全相同 |
| C3 | **承重：p12 降幅 ≥30%** | **PASS 37.37%**（R436 = 29.28%） |
| C3b | 预注册预测命中（±0.5pt） | PASS 预测 37.37% / 实测 37.37%，偏离 0.0 pt |
| C4 | 门决策与冻结基线逐轮一致（FN/FP/acc） | PASS per_turn 全同；FN=0 FP=0 acc=1.000 |
| C5 | **缓存前缀单调性**（相邻远端调用：前一次请求是后一次的逐字前缀） | PASS A 10/10 对、BRJ 6/6 对，0 违例 |
| C6 | 泄漏形状：跳过轮条目零块、远端轮条目必有块、首轮免检 | PASS BRJ 跳过轮[2,3,4,5] 泄漏=0，24/24 条目**逐字等于**机检派生的原文；A 无跳过轮 |
| C6b | **因果归因**：同臂相对 R436 冻结档案的差 = 被移除块质量 | PASS 19557→17319，移除 2238 tok，逐调用偏离 0.0 |
| C7 | 确定性复跑 | PASS Δ=7 tok（0.040%），**残差完整归因** = 系统提示内嵌 run 目录路径长度差 2 字符 |
| C9 | 负控「无本地设备」（BP） | PASS r1 skip=0、远端兜底 7、降幅 −6.92%（净亏）⇒ 增益确实依赖真实 r1 设备 |

**诚实边界**：① 远端 token 为桩侧估算（`prompt/completion_tokens_est`），非真实计费，绝对值不可当账单；
② 未做真机远端（DeepSeek）重放；③ 本轮**未跑 p8 网格**（承重已由 p12 达成；p8 按同一机理应进一步上升，属外推）；
④ C5 只能证明**桩侧请求序列**的前缀单调性，不等于 provider 侧真实命中率（真机命中率本轮未测）。

## 2. 臂矩阵（`compare_r438.py`，R438 二进制 `bin_sha16=…`）

| 臂 | 调用 | tokens | 降幅 | FN/FP/aCC | r1 skip | J 本地 |
|---|---|---|---|---|---|---|
| A（关闸基线） | 11 | 27654 | 0.0% | 0/4/0.636 | 0 | 0 |
| **BRJ（门+J本地+修复）** | 7 | **17319** | **37.37%** | 0/0/1.000 | 4 | 7 |
| BRJ2（同臂复跑） | 7 | 17326 | 37.35% | 0/0/1.000 | 4 | 7 |
| BP（无设备负控） | 18 | 29569 | −6.92% | 0/4/0.636 | 0 | 0（远端兜底 7） |

## 3. 改动清单

- `src/agent/IndustrialAgentV2.cs`：跳过分支内 `message.SentContent = outboundText` + 遥测 `local_gate_skip_history`
  （`persisted_chars` / `would_be_chars` / `dropped_chars`，形状可观测，非仅注释）。
- `eval/rover/r438/{predict_r438.py,verify_r438.py,run_arm.sh,settle_r438.py,compare_r438.py,channel_marks.py}`。
- `docs/plans/v0.58.0-r438-localskip-no-replay.md`（预注册判据 + 预测，先于代码落盘）。
- AOT：`$HOME/.dotnet/dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_r438`，
  **IL 警告 0**、native 形态、退出码 0；臂矩阵由该二进制跑出。

## 4. 复现

```bash
export DOTNET_ROOT="$HOME/.dotnet"
$HOME/.dotnet/dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_r438
cd eval/rover/r438
R438_GRID=p12 bash run_arm.sh A   47980 47982     # 基线
R438_GRID=p12 bash run_arm.sh BRJ 47986 47988     # 处理臂
R438_NS=-2 R438_GRID=p12 bash run_arm.sh BRJ 47990 47992   # 确定性复跑
R438_GRID=p12 bash run_arm.sh BP  47994 47996     # 无设备负控
python3 verify_r438.py && python3 compare_r438.py
```
