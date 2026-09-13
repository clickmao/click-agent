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
3. **「计算」是减法**（wall − 盘等待），尚未直测 ⇒ 下轮（步 2）以「权重常驻内存的反量化+点积微基准」直测。
