# R408 证据 — 本地 GGUF 引擎退役 / llama.cpp 进程化接入

日期: 2026-09-14 · 主机: 2 vCPU (AMD EPYC 9754, SMT 1 物理核) / MemTotal 3.574 GiB / avx512f,avx512dq,avx512ifma / 磁盘 19 G 可用
模型: `/tmp/models/r1-distill-qwen-1.5b-q4km.gguf` (1,117,320,800 B, sha256 `1741e5b2d062b07acf048bf0…`)
prompt: 96 B, sha256 `d1e94bf720adbab7b376d0014bfeb01a8c03864cae7c4a1110ab9be5750fa947` (R407 权威 prompt 字节)
llama.cpp: `/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server` (0.1.0-dev, commit 4df29be, `-DGGML_NATIVE=ON`)

## A. 同机同环境 A/B（回答「你是在本机同环境测试的么？」）

| 臂 | 实现 | 参数 | Prompt t/s | **Gen t/s** |
|---|---|---|---|---|
| llama.cpp `llama-cli` | 官方二进制 | `-t1`, K/V **f32**, flash-attn off, 关采样过滤 | 23.8 | 11.1 |
| llama.cpp `llama-server`（**新后端**） | 同一二进制 | 同左 | 33.049 | **17.891** |
| 本引擎 AOT | `/tmp/aot-r407/agent.rover` | 同 prompt 字节 | — | **0.2017** |
| 本引擎 JIT | R407 `gen-dump.json` | 同上 | — | 0.375 |

**全部同机、同模型文件、同 prompt 字节、greedy 24 token**（判据预注册于 `/tmp/probe-r408/ab_llamacpp.sh`）。
⇒ 差距 **48× ~ 89×**（对 AOT 4957 ms/token）。

归因（我方 AOT 分阶段直测）: `ffn = 61080.7 ms (87.4%)` / `attn = 7875.8 ms (11.3%)` / `lm_head = 923.0 ms (1.3%)`
I/O 排除: `disk_read_bytes=0`、`majflt=0`（纯页缓存）⇒ **不是 I/O 瓶颈，是权重流式内核吞吐**。
内核吞吐: 0.93 GB/pass ÷ 3.59 s ≈ **181 MB/s** vs llama.cpp ≈ **10 GB/s** ⇒ **~55×**。
副读数: **AOT 比自家 JIT 慢 1.86×**（4957 vs 2668 ms/token）。原因未定位 ⇒ 标「待确认」，不编解释。

## B. 新端口数值对账 — 24/24 token id 逐位相同

```
agenthost --llamacpp --model /tmp/models/r1-distill-qwen-1.5b-q4km.gguf \
  --prompt-file /tmp/probe-r408/prompt.txt --max-tokens 24 --expect-ids <24 ids> --json eval/rover/r408/e2e-generate.json
```
`IdsMatch=true`，exit 0；文本 `\nTo calculate 12 multiplied by 12, I start by breaking down the multiplication into simpler parts.`
（与 R407「llama.cpp f32-KV = 我方 = numpy oracle」三臂一致的文本相同）
ids: `151648,198,1249,11047,220,16,17,54916,553,220,16,17,11,358,1191,553,14719,1495,279,46444,1119,34288,5479,13`

> **归档口径（R411-V 补注）**：本仓库只归档了 **AOT 臂**产物 `eval/rover/r408/aot-generate.json`（其 `IdsMatch=true`、`PredictedPerSecond=17.64` / `PromptPerSecond=34.458`，与 §I 逐字一致）；上面这条 JIT 复现命令当时写入的 `e2e-generate.json` **从未入库**（旧登记行却引用了它 ⇒ 已按 R411-V 改指 `aot-generate.json`）。复现 JIT 臂时该文件会重新生成，届时再归档。

## C. 嵌入端口（llama.cpp `/v1/embeddings`）

`dim=768`、`‖v‖=1.000000`（服务端已 L2 归一）、`sha256=d53363214ddc4d95321c623cec4535d419f303ad85cfa09dd290c4236b0be0d1`
跨实现对账（同文本「人工智能代理框架」，两侧均已归一）: 旧自研 `agent.embedcpu`(AOT) 向量 **cos = 0.158573**
⇒ 与 R404 记录（cos 0.21~0.31，判据 ≥0.99）同向 ⇒ **自研前向是错的那一侧，llama.cpp 是参考侧**；R404 那一类缺陷随退役消失。
⇒ 也就解释了 R404 为何反复定位不到：错在自研前向本身，而当时把 llama.cpp 当"另一个实现"来对账。

## D. 过程中发现的既有产品缺陷（新增，非本轮引入）

1. **`agent.host --embed` 崩溃**：走 `agent.llamalocal.RemoteEmbedder`（unix-socket daemon），daemon 离线时**抛未处理异常 ⇒ core dump，exit 134**（本轮实测）。注释声称「daemon 离线 → hash 兜底语义」与实现不符 ⇒ 该 KPI（reply_rel）路径既可能长期用非语义向量、又会直接崩进程。
2. **传输层跨平台不成立**：`src/agent/llamalocal/RemoteEmbedder.cs` 硬编码 `AddressFamily.Unix` + `LlmManagerHost` 默认 `sh -c` spawn ⇒ Windows 无 unix socket、且违反零 shell 铁律。这正是「我要跨平台的」所指的缺口。
3. **llama.cpp 形态约束**：`/v1/embeddings` 必须启动时加 `--embeddings`，且该开关**与文本生成互斥** ⇒ 生成/嵌入必须是两种进程形态（各自专用模型），不能共用一个进程。

## E. 复现命令

```bash
export DOTNET_ROOT="$HOME/.dotnet"; export PATH="$HOME/.dotnet:$PATH"
export AGENTFRAMEWORK_LLAMA_BIN=/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server
# 生成 (对账 24/24)
dotnet src/agent.host/bin/Debug/net10.0/agenthost.dll --llamacpp --model /tmp/models/r1-distill-qwen-1.5b-q4km.gguf \
  --prompt-file /tmp/probe-r408/prompt.txt --max-tokens 24 --json eval/rover/r408/e2e-generate.json
# 嵌入
dotnet src/agent.host/bin/Debug/net10.0/agenthost.dll --llamacpp --model /tmp/models/bge-base-zh-v1.5-q8.gguf \
  --embed-text "人工智能代理框架" --vec-out /tmp/probe-r408/new-vec.json --json eval/rover/r408/e2e-embed.json
```

## F. 覆盖度自陈（诚实边界）

- 已测: 单请求生成对账、单文本嵌入、进程启停、端口计数、provider 不可用负控（代码契约）、**产品 DI 路径与命令路径指纹一致**、退役后整链编译。
- **未测**: 并发多请求/队列、长上下文（>4096）、流式 SSE 增量、超时/杀进程恢复、Windows/macOS 实机（二进制形态仅本机 Linux 验证）、AOT 发布后 `--llamacpp` 实跑（见 §H）。

## G. 产品线切换（P2，已办）

| 变更 | 旧 | 新 | 证据 |
|---|---|---|---|
| DI `ITextEmbedder` | `agent.embedcpu.BgeCpuEmbedder`（纯托管 BERT 前向） | `agent.llamacpp.LlamaCppTextEmbedder`（懒启动专用 llama-server `--embeddings`） | 构建 0 error；`IsAvailable` 不可用即回 `NullTextEmbedder`（行为兼容） |
| `agenthost --embed`（reply_rel KPI 取向量路径） | `RemoteEmbedder`（unix socket；daemon 离线 ⇒ **未处理异常 core dump exit 134**） | llama.cpp 嵌入；不可用 ⇒ `provider_unavailable` + exit 4 | 旧路径 core dump 已实测复现；新路径 exit 0 |
| 向量一致性 | — | `--llamacpp --embed-text` 与 `--embed`(DI) 同文本向量 `sha256 = d53363214ddc4d95321c623cec4535d419f303ad85cfa09dd290c4236b0be0d1`（两侧独立代码路径） | 一致 ⇒ 确定性 + 接线正确 |

## H. 退役账（P2）

- 删除: `src/agent.rover/{gguf,quant,infer,runtime,token,cli}` + `Program.cs` + `gpu/Vulkan{Backend,MatMulBackend}.cs` = 40 文件 / **10,319 LOC**；`src/agent.embedcpu/**` = 10 文件 / **647 LOC**（整工程）；9 个引擎测试文件；测试工程内 12 条 rover 同源编译登记。
- 保留（非 GGUF，产品共享源）: `agent.rover/formal/**`（形式化内核，产品节点闸门 + `dcrval` 用）、`agent.rover/gpu/spirv/**`（SPIR-V 汇编器 + 独立校验器）。
- `agent.rover.csproj`: `OutputType=Exe` → `Library`，Silk.NET.Vulkan/Core 与 TensorPrimitives 依赖移除（**纯 BCL**）⇒ 预期 AOT 的 6 条 `Silk.NET.Core` IL 警告随之消失（见 §I）。
- 退役后 `dotnet build src/agent.tests`（覆盖产品整链）**exit 0**。

## I. 全量回归 / AOT（R408 实测读数）

- **全量回归**: `Passed! - Failed: 0, Passed: 1063, Skipped: 0, Total: 1063`（TEST_EXIT=0）
  （退役前 1130/2/1132 → 退役后 1063/0/1063：差额 = 随源退役的 69 个引擎测试；剩余 2 个红已按根因修掉，见下）
- **退役引入的 2 处红及其根因处置**（不是掩盖）:
  1. `VulkanLoaderParityTests.Requested_ApiVersion_Matches_Engine_SilkNet_Path` —— 源码级反漂移锚点指向已删的 `src/agent.rover/gpu/VulkanBackend.cs` ⇒ 改名 `Requested_ApiVersion_Arithmetic_Is_Consistent` 保留产品侧 `VulkanNames` 版本算术断言（锚点消失的原因写进测试注释）。
  2. `VerificationFormTests.Registry_Exists_And_HasNoViolations` —— `docs/verification-registry.json` 有 3 行 `evidence_path` 指向已删文件 ⇒ 把这 3 行**改写为 R408 真实形态**（`llamacpp.process.boundary` / `llamacpp.embedding.port` / `engine.retired.no_local_gguf`），并给 2 行环境类历史行补 `gap_note`；`updated_round=R408`，43 行不变。
- **AOT 发布**: `dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/aot-r408` ⇒ **exit 0，IL 警告 0 条**（原 6 条 `Silk.NET.Core` 警告随退役消失）; 产物 `/tmp/aot-r408/agenthost` = 14,778,256 B。
  - AOT 产物 `--llamacpp` 24 token 对账: **IdsMatch=true, exit 0**, `PredictedPerSecond=17.64 / PromptPerSecond=34.458`, 计数 `Requests=1 / TokensGenerated=24 / EmbeddingsServed=0`（与响应一致）。
  - AOT 产物 `--embed`: exit 0，向量头 `[0.018618265,-0.031712163,0.016895808,…]`（与 JIT 路径同值）。
  - 发布坑（已登记于 `aot.publish.zero_il` 行，本轮又踩一次）: **不要带 `-p:PublishAot=true`**（全局属性会污染 `agent.io` ⇒ `NETSDK1207`）；AOT 开关在 `agent.host.csproj` 内。
- **机检（零 P/Invoke）**: `grep -r "DllImport\|LibraryImport" src/ --include=*.cs` ⇒ 0 命中（见 `engine.retired.no_local_gguf` 行的 evidence_cmd）。

