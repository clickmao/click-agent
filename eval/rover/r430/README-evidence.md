# R430 证据 — 判定输入指纹 ⇒ 引擎侧总槽位 (决策路径逐位可复现)

本文件由 `make_evidence_r430.py` 从机检 JSON + 遥测逐字节哈希 + 服务端日志生成（非手抄）。

## 1. 因果链

1. R429 已钉死决策路径的**前缀缓存**（cache_prompt=false），但同文门判文本仍 4 种取值 ⇒ P5c 未过。
2. 本轮先加**输入指纹**（prompt / 请求体 / 角色种子，只观测）⇒ 判定「输入是否逐位相同」。
3. 真机（臂 C / k8r，改动前二进制）：4 次门判 prompt_sha 与 request_sha **各只有 1 种取值**，
   而输出 raw 逐字节哈希 **4 种** ⇒ 输入可复现成立，漂移在**引擎侧**（H1 证伪 / H2 成立）。
4. 机制（传输级探针）：本仓库 llama.cpp 构建的 `-np` 默认 = **4 槽**（启动日志实证）⇒ 门判与关系判官
   等**并发在途**请求进同一批 ⇒ 每序列批形状/分块随调用序列变化 ⇒ 浮点归约顺序变 ⇒ 同一输入走向不同轨迹。
5. 修法：本地通道服务端**显式**声明总槽位 = 1（`-np 1`，真串行；不依赖构建默认）⇒ 真机同文 4 次门判
   raw 逐字节**同一**。

## 2. 判据与读数

| 判据（预注册）| 读数 | 判定 |
|---|---|---|
| P1 串行控制（默认槽位，无并发）| token ids `[75, 75, 75]` | PASS |
| P2 机制：并发在途（默认 4 槽）| A 序列变体数 **2** （['A_tok=105', 'A_tok=105', 'A_tok=108']） | 坐实 |
| P3 隔离：`-np 2` + id_slot 分离 | 变体数 **1** | 备选（本轮未采用）|
| P4 修法：并发 + 强制 `-np 1` | 变体数 **1** | PASS（修法在传输级验证） |

## 3. 真机两臂（同一 k8r 网格 / 同一 role）

| 项 | 改动前（`/tmp/pub_r430`，sha `c5706b5f`）| 修法后（`/tmp/pub_r430b`，sha `bb104dd7`）|
|---|---|---|
| 门判序列 / 遥测 raw_len | 决策 `Skip/Skip/Skip/Skip`；cache_n `0/0/0/0`；pinned `1/2/3/4`；raw_len `122/129/113/111` | 决策 `Skip/Skip/Skip/Skip`；cache_n `0/0/0/0`；pinned `1/2/3/4`；raw_len `127/127/127/127` |
| 门判 raw 逐字节 sha16（4 次）| `53855c3b87964492`, `81995565ea3d67df`, `3e20e31b0c37b6f5`, `1d0222a66a14225f` | `340ba10faeb3a0a8`, `340ba10faeb3a0a8`, `340ba10faeb3a0a8`, `340ba10faeb3a0a8` |
| prompt_sha / request_sha 取值数 | 1 / 1 | 1 / 1 |
| 远端调用 / token（估）| 2 / 2053 | 1 / 1996 |
| 归因机检 | alignment=True attribution=True 被问门轮=[2, 4, 6, 8] | alignment=True attribution=True 被问门轮=[2, 4, 6, 8] |

请求字段摘要（两臂同一常量, 机检 `req_fields`）：`np=512;t=0;sp=temperature;cp=0;seed=0;tk=0;tp=1;mp=0;rp=1`

## 4. 环境真值（服务端日志）

- 启动行 `n_slots`：未显式 `-np` 时 = **4**；`-np 2` 时 = 2；n_ctx_slot = 4608
- `n_threads`：['1']（生成侧 `-t 1`，非并发因素）
- 服务端日志副本：`eval/rover/r430/server-probe.log`（含槽位并发在途行：两 task 生命周期重叠）

## 5. 形态与回归

- V0 形态闸：被测 AOT 原生 = True（15180528 B，env -i 自启 rc=0）；IL 负控必拒 = True（apphost 78256 B，rc=131）
- AOT publish（`/tmp/pub_r430b`）：IL 警告 **0**；`agenthost` 15,180,528 B；sha256 前缀 `bb104dd7f2a021b0`
- 全量回归：**1242/1242 绿**（R429 1223 + 本轮 8 指纹例 + 11 总槽位例）；子集 26/26

## 6. 排除项 / 诚实边界

1. **未测**「修法后判定文本与角色/远端链路的质量是否变化」——本轮只测可复现性与 KPI 计数。
2. `-np 1` 的代价是本地通道**真串行**（判官本地调用与门判互相排队）；本轮未量化墙钟增量上限。
3. G3（`-np 2` + id_slot）本次亦 3/3 相同，但依赖**每次调用钉槽位**；本轮采用 `-np 1`（配置即隔离，无调用侧依赖），
   G3 仅作备选记录，不作为能力宣称。
4. 探针 v1 曾因「渲染 /apply-template 在起服务前」与末段 `id_sets` lambda 取值 bug 未落盘；
   v2 已修并**增量落盘**（`probe-r430-concurrent-v2.json`）。
5. 遥测 raw 逐字节哈希取自产物 telemetry（外部真值为**逐请求计数**：`remote_calls` 由桩落盘），
   两者同源不可互证的部分已在第 3 节分列。
6. 本节读数均为**单机单次**；P2/P4 的变体数在不同批次可能不同（机制结论不依赖具体变体个数）。

## 7. 复现命令

```bash
# 机制探针（起自带 llama-server：默认槽位 vs -np 1）
python3 eval/rover/r430/concurrent_probe_v2.py
# 真机两臂
AGENTFRAMEWORK_HOST_BIN=/tmp/pub_r430/agenthost  R430_NS=-r430post1 bash eval/rover/r430/run_arm.sh C k8r 47920 47921 /home/agentuser/AgentFramework/skeptic.rbin
AGENTFRAMEWORK_HOST_BIN=/tmp/pub_r430b/agenthost R430_NS=-r430fix1  bash eval/rover/r430/run_arm.sh C k8r 47930 47931 /home/agentuser/AgentFramework/skeptic.rbin
```
