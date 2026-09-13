# R402 · 第 1 步：把「≈20–33 s/token」拆成盘读与计算（归因，不是优化）

- 轮次: **R402 步 1**（性能线；只做**归因测量**，不改产品链行为）
- 上游: `docs/plans/v0.26.0-r400-rover-generation-chain.md` §7.2（靶点选择：批 prefill vs 线程 vs mmap 策略）
- 起因: R399/R400 实测 ≈20–33 s/token 被判为「不可交互」，但**没有一个数字回答「慢在哪」**。
  在归因之前选靶点（加线程？批 prefill？改 mmap 策略？）等于拿未归因的数字做决策。
- 判据**预注册**（写死在脚本里，防事后凑解释）见 `scripts/r402_io_attribution.py` 头部：
  `disk_read_bytes/pass ≈ 模型体积 ⇒ I/O 主导（靶点=批 prefill/预读）`；
  `≪ 模型体积 ⇒ 页缓存命中 ⇒ 靶点=计算（SIMD/线程/反量化）`。
- 证据（**随仓库**，见 `eval/rover/r402/README.md`）: `eval/rover/r402/io-attribution-run3.json`（主证据）、
  `eval/rover/r402/io-attribution-run2-doublecounted-device.json`（设备通道双计负控留档）、
  `eval/rover/r402/run1-console-capture.txt`（第 1 次运行控制台捕获）;
  驱动脚本 `scripts/r402_io_attribution.py`（重跑写入 gitignore 的 `data/probe/r402/`）

## 1. 三条互相独立的通道（必须同向才下结论）

| 通道 | 读法 | 为什么需要它 |
|---|---|---|
| ① 进程侧 | 被测程序自印 `/proc/self/io` `read_bytes`（`rover forward` 的 `io{}` 行，R402 新增） | 精确归属到被测进程，但属**自我报告** |
| ② 设备侧 | `/proc/diskstats` 整盘累计读扇区增量（**只算整盘** `vda`，分区行会双计） | 内核视角，不依赖被测程序的自我报告 |
| ③ 裸读参照 | 新 CLI `rover readbench`：同机同文件、**零数学运算**的顺序读 / mmap 触碰 | 给出「同样多字节、不做任何计算要花多久」的物理地板 |

机器事实（本机，`machine` 段入档）：`MemTotal=3,747,744 kB (3.574 GiB)`、`Cached=2,475,728 kB (2.36 GiB)`、
`MemFree=247,036 kB`、`nproc=2`、swap 1.9 G 中已用 921.5 MB；
模型 `prover7b-q4km.gguf` = `4,223,362,304 B (3.933 GiB)` = **RAM 的 1.13 倍**；
`/` = `/dev/vda2` ext4（**真块设备**，非 tmpfs —— 已核，否则本报告全部作废）。

## 2. 真机读数（三次重复跑，同命令）

| 臂 | 1-token 墙钟 | 2-token 墙钟 | 每 pass 盘读 / 模型体积 | 裸读 stream / mmap |
|---|---|---|---|---|
| 第 1 次 | 15.97 s | 29.61 s | **0.912** | 436.0 / 364.3 MiB/s |
| 第 2 次 | 25.02 s | 48.10 s | **0.879** | 491.5 / 368.0 MiB/s |
| 第 3 次 | 22.66 s | 42.81 s | **0.765** | 544.0 / 229.2 MiB/s |

第 3 次（设备通道口径已修正，两通道相符）：

```
forward_1tok  wall=22.66 s  passes=1  disk_read_bytes=3,232,411,648 (=0.766×模型)
             streamed_bytes_per_pass=4,218,372,096  ledger_sweeps=0.999  majflt/pass=1,482
             设备通道(整盘 vda)=3,251,081,216  ⇒ 设备/进程 = 1.006×
bare_read    stream=544.0 MiB/s（pass0 3.24 GB@430.9 MiB/s, pass1 **2.00 GB@737.5 MiB/s**）
             mmap=229.2 MiB/s   stream64=320.5 MiB/s   mmap64=178.1 MiB/s
cache_reuse_delta{cold_minus_warm_per_pass_over_model = 0.0}   ← 冷页臂与默认臂逐字节相同
```

## 3. 结论（按判据）

1. **I/O 主导成立，但计算不是零头**：每 pass 必须从块设备重读 **76.5%–91.2%** 的权重字节
   （3.23–3.85 GB/pass，三次同向）。用「同机同文件的裸读速率」作分母换算盘等待：
   第 1 次 8.4–10.1 s / 15.97 s（**53–63%**）、第 2 次 7.2–9.6 / 25.02（**29–38%**）、
   第 3 次 5.7–13.4 / 22.66（**25–59%**）。⇒ **盘等待与计算都是一阶项**，两个靶点都不能只挑一个。
2. **页缓存不可依赖（本机实测）**：`Cached=2.36 GiB`，所以裸读的**第二次** pass 只从盘读 2.00 GB
   就跑到 737.5 MiB/s（缓存确实留住了约 2 GB）；但**前向**的 pass 缓存命中只有 9–24%。
   解释（**解释不是测量**）：前向 sweep 慢（22 s vs 裸读一次 5.4–9.3 s），给内核留了更多回收时间，
   且进程 RSS（R400 实测峰值 1.90 GiB）挤压页缓存。⇒ 优化不得以「会被缓存」为前提。
3. **引擎侧不存在任何缓存复用机制**：`--drop-pages` 冷页臂与默认臂的每-pass 盘读差
   = **0.000**（三次同向）⇒ 现在的复用度是内核给的，不是引擎做的；引擎没有可调的「复用」旋钮。
4. **预读/mmap 提示无空间可挖（负结果）**：裸读 64 MiB 块 = 320.5 MiB/s，**低于** 8 MiB 块（544.0）；
   mmap 提示窗 64 MiB = 178.1 MiB/s，**低于** mmap 8 MiB（229.2）。⇒ 按「数据先行」，
   不实现预读优化（零收益空间不进代码），只留读数。
5. **本机天花板（给 R401 的决策输入）**：即使把盘读压到 0，剩下的**计算**是 9.2–17.0 s/pass（2 vCPU）
   ⇒ 0.06–0.11 tok/s，与远端 API（470.2 tok/s，R400 实测）差 **≈4,300–7,800×**。
   ⇒ **「本机 rover 当交互级解法后端」在物理上不成立**，不是缺优化；R401 的解法级 KPI 对比
   在本机**应改口径**（离线/验证用引擎），不应继续按「吞吐对比」立项。
6. **批量的收益上界**：单 token 一次前向 = 1 次全权重 sweep ⇒ `T(N) ≈ 盘读 + N×计算`，
   即批量只摊薄盘读：per-token 由 22.66 s 趋于 8.4–17 s（**1.3–2.7×**），
   且真实值很可能**优于**这个线性式（同一次 sweep 里权重被 N 列复用，边际计算成本下降）。
   **必须实测**，不能拿这个线性式当结论 —— 这正是步 2/3 的靶点。

## 4. 本轮修正的三处「看起来对」的失效

| # | 失效形态 | 证据 | 处置 |
|---|---|---|---|
| 1 | **R400 台账口径错**：`流式字节 177,440,440,320 B ⇒ ≈22.2 GB/token（≈5.3× 模型体积）` —— 分子含 37 prefill + 8 decode 共 45 个 pass，分母只除 decode 的 8 步 | 同报告 §96/§142 自己写的是「每 token 流式扫 ≈4.0 GiB」⇒ 报告内部自相矛盾 | 正确值 = 177,440,440,320 / 45 = **3.943 GB/token**（≈0.94× 模型体积）；已在 R400 报告 §3 加修正行 |
| 2 | **设备通道双计**：首版 `/proc/diskstats` 正则 `vd[a-z]+\d*` **把 `vda1` 也匹配了** ⇒「只算整盘」与「全加」两个数几乎相等，看着像「没有双计」 | 修正后 guard 实测 `naive=6,502,662,144` vs `whole=3,251,081,216` = **2.00×** | 正则收紧为 `$`（不带 `\d*`）；**双计值与正确值一并落盘**做负控；口径踩坑写进脚本注释 |
| 3 | **墙钟抖动被当成读数**：同一个 1-token 前向三次跑出 15.97 / 25.02 / 22.66 s（极差 **1.57×**）；裸读 mmap 也从 368 → 229 MiB/s | 见 §2 表 | ⇒ 本机「秒/token」**不是**稳定 KPI。归因只用**计数器比值**（0.765/0.879/0.912 与 ledger 0.999 稳定），秒表只作区间 |

## 5. 代码落点（R402 步 1）

| 文件 | 锚点 | 作用 |
|---|---|---|
| `src/agent.rover/runtime/ProcIo.cs` | `ProcIoSnapshot.Capture/Parse/Delta`、`IoThroughput` | 进程 I/O 与缺页读数；口径（每 pass 分母）的**单一来源** |
| `src/agent.rover/infer/ForwardPass.cs` | `ForwardStats.Io/.Passes/.DiskReadBytesPerPass/.StreamedBytesPerPass/.DiskReadRatio` | 前向首尾各取一次读数，差值为本次前向真值 |
| `src/agent.rover/cli/ForwardCli.cs` | `io{}` / `io_scope{}` 行 | 把归因读数与依据规则一起打印（规则入输出，防事后改口径） |
| `src/agent.rover/cli/ReadBenchCli.cs` | `readbench <file> --mode stream\|mmap --chunk-mb N --passes N` | 裸读地板；自带 `readbench_scope{disk_path_engaged=…}` 判「这次到底吃没吃盘」 |
| `src/agent.rover/cli/RoverCli.cs` | 分派 `readbench` + Usage | 接线（Known/switch 双表同轮更新） |
| `src/agent/agent.csproj` | 共享源 `../agent.rover/runtime/ProcIo.cs` | 纯 BCL，供测试工程复用（与 `Sampler.cs` 同模式） |
| `src/agent.tests/RoverProcIoTests.cs` | 6 条 | 解析 / **字段偏移**（`/proc/self/stat` 的 minflt=idx7、majflt=idx9）/ 缺字段与畸形一律 `available=false` **不记 0** / delta / 每-pass 分母口径负控 |
| `scripts/r402_io_attribution.py` | — | 三通道取证驱动（含设备双计负控、裸读分母区间、不可用即标 unavailable） |

### 复现命令

```bash
export DOTNET_ROOT="$HOME/.dotnet"; export PATH="$DOTNET_ROOT:$PATH"
dotnet build src/agent.rover/agent.rover.csproj -c Release --nologo -v q
dotnet test src/agent.tests/agentframework.tests.csproj -c Release --nologo -v q --filter "FullyQualifiedName~RoverProcIo"
# 单臂（约 25 s）
src/agent.rover/bin/Release/net10.0/agent.rover forward /tmp/models/prover7b-q4km.gguf --tokens 1000 --ctx 4 | grep -E "^(io|stream|residency)"
src/agent.rover/bin/Release/net10.0/agent.rover readbench /tmp/models/prover7b-q4km.gguf --mode stream --chunk-mb 8 --passes 2
# 三通道全量（约 3–5 min，含 6 臂）
python3 scripts/r402_io_attribution.py --json data/probe/r402/io-attribution-run3.json   # 证据副本见 eval/rover/r402/
```

## 6. 诚实边界

- **墙钟不可复现到 ±5%**：本机为共享宿主，同题重复跑极差 1.57× ⇒ 绝对秒数只作区间；
  凡结论只建立在计数器比值上（每-pass 盘读比、ledger 当量、冷页差）。
- **盘等待是估计而非直测**：分母取同机同文件的裸读速率（stream/mmap 两条路径给上下界）。
  裸读是**顺序**读、前向是**逐张量缺页触碰**，故真实盘等待倾向区间**上沿**。
- **「计算」是减法得到的**（wall − 盘等待），尚未直测。要把它变成一等读数，需要权重常驻内存的
  反量化+点积微基准（步 2 靶点）。
- 单机单盘（`vda`，2 vCPU，MemTotal 见 §1），结论**绑定本机**；不推广到其它机型。
- 本轮**不改**产品链行为、不做任何优化 ⇒ 不产生吞吐提升，只产生「靶点选择的依据」。
- 第 1 次运行的原始 JSON 被第 2 次覆盖（留 `run1-console-capture.txt` 原样捕获 + 明示丢失）——
  账目如实留档，不用估算值补。

## 7. 下轮候选（R402 步 2，取自本轮数据）

1. **计算直测微基准**（首选）：权重常驻内存的反量化+点积吞吐（1 线程 vs 2 线程），
   把「计算」从减法变成直测 —— 两个杠杆（批量/线程）的收益上界都由它决定，先量它最省。
   判据：产出 `MB/s/核` 与 2 线程加速比；若 <1.3× 则「加线程」升不了级，直接进批量臂。
2. **批 prefill A/B（N=4）**：在 `forward` 上开批量臂，同题（37-token prompt）对账
   per-token 秒数是否落进 8.4–17 s 区间（预期 1.3–2.7×，可能更优）。
   反向断言：批量臂的 `passes` 必须下降（37 → ⌈37/N⌉），且输出 logits 与逐 token 路径**数值一致**。
3. **R401 口径修正**（由本轮 §3.5 直接推出）：把「本机 vs 远端吞吐对比」改为
   「离线引擎正确性/可对账性」口径，避免继续为一个物理上不可达的目标立项。
