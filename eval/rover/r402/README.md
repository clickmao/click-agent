# R402 · rover 性能归因读数（tracked 副本）

`data/` 目录被 `.gitignore` 忽略，故把 R402 步 1 的**原始读数副本**放这里，保证证据可随仓库分发/复核。

| 文件 | 说明 |
|---|---|
| `io-attribution-run3.json` | **第 3 次**运行（设备通道口径**已修正**；进程/设备两通道相符 1.006×）——报告主证据 |
| `io-attribution-run2-doublecounted-device.json` | 第 2 次运行（设备通道**双计**未修正：`whole` 与 `naive` 几乎相等而掩盖了正则错；留作负控留档） |
| `run1-console-capture.txt` | 第 1 次运行的原样控制台捕获（其原始 JSON 被第 2 次覆盖，**如实留档**，不用估算补） |

## 复现（重跑会写入 gitignore 的 `data/probe/r402/`）

```bash
export DOTNET_ROOT="$HOME/.dotnet"; export PATH="$DOTNET_ROOT:$PATH"
dotnet build src/agent.rover/agent.rover.csproj -c Release --nologo -v q
python3 scripts/r402_io_attribution.py --json data/probe/r402/io-attribution-run3.json   # 约 3–5 min
```

## 读这些数时要带上的三条边界（详见 `docs/reports/r402/io-attribution.md`）

1. **墙钟不可复现到 ±5%**：同题同命令的 1-token 前向三次为 15.97 / 25.02 / 22.66 s（极差 1.57×，共享宿主）。
   结论只建立在**计数器比值**（每-pass 盘读比、ledger 当量、冷页差）上。
2. **「盘等待」是区间估计**：分母取同机同文件的**零运算裸读**速率（stream 与 mmap 两条路径给上下界）；
   裸读是顺序读、前向是逐张量缺页触碰 ⇒ 真实盘等待倾向区间**上沿**。
3. **「计算」是减法**（wall − 盘等待）；步 2 的直测微基准只覆盖 2 张量（见下），全模型计算吞吐仍是估计。

## 步 2 微基准（1 vs 2 线程）· 裁定（R411-V 补登记）

`compute-bench.json`（R407 提交 `cd8feeb` 入库；**此前未出现在本表，属孤儿归档**）：
2 张量 × `threads∈{1,2}` × `reps=3`，权重常驻内存（`disk_read_bytes=0` / `majflt=0`）。

| 张量 | 1 线程 | 2 线程 | 加速比 | `y_hash` 一致 |
|---|---|---|---|---|
| `token_embd.weight` (Q4_K) | 464.5 ms / 0.5079 GB/s | 442.7 ms / 0.5329 GB/s | **1.049** | ✅ |
| `blk.0.ffn_down.weight` (Q6_K) | 92.5 ms / 0.3999 GB/s | 89.5 ms / 0.4134 GB/s | **1.034** | ✅ |

**裁定**：对照 `docs/reports/r402/io-attribution.md` §7.1 预注册判据「2 线程加速比 <1.3× ⇒ 加线程升不了级」
⇒ **实测 1.034–1.049（<1.3×）⇒ 不升级**。机制解释：本机 2 vCPU = **1 物理核 + SMT**，无第二物理核可并行。
**边界**：`estimates[].est_ms_per_token`（8866→8488）为原产物自述，外推公式随生产者 CLI 删除（R408）⇒ 不可复核。
