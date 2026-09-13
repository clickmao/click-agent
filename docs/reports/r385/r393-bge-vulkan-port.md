# R393 · 本地 BGE 接入 Vulkan GPU 执行端口（真机对账 + 驱动约束取证）

> 轮次：**R393**（2026-09-13）。用户令（逐字）：**"agent 本地bge也需要加vulkan gpu运行端口"**。
> 判据口径：端口存在且**真机执行**、与参考实现**数值对账**、**端口确实被使用**（防空心）、`--selftest` 机器判定、无设备时**显式失败不静默回退**。
> 证据源：`/tmp/r393/`（`embed_evidence.log` · `embed_vk_pool.log` · `aot_embed_vk.log` · `final.log` · `build.log` · `full_test.log`）；一次性探针 `/tmp/r393probe`（**不入产品**）。

---

## 1. 因果链：为什么是"端口"，以及端口长在哪一层

本地 BGE（`bge-small-zh-v1.5`，4 层 / hidden 512 / ffn 2048）一次嵌入的算力热点 = **每层 6 次矩阵乘**（q/k/v/attn_output/ffn_up/ffn_down）⇒ 一次嵌入 **24 次 [seq,in]×[in,out]** 乘累加。若把"GPU 版本"写成第二个前向实现，就会立刻产生**两份语义**（LayerNorm/注意力/GELU/池化的实现漂移），此后任何一侧改动都要双改双测 —— 这是 R368 教训表 §10.2（同构多表示的形状静默错）的同类风险。

因此本轮的落点不是"再写一个 GPU 嵌入器"，而是**端口（port）+ 单一前向**：

| 层 | 文件 | 职责 |
|---|---|---|
| 端口契约 | `src/agent.embedcpu/MatMulBackend.cs` | `IMatMulBackend.MatMulAdd(x,w,b,seq,in,out)`；语义 `y[seq,out] = x·Wᵀ + b`（GGUF `[out,in]` 行主序）；纯函数、长度恰为 `seq*outDim` |
| CPU 实现（默认） | 同上 `CpuMatMulBackend` | `TensorPrimitives.Dot`（SIMD 多累加器） |
| 前向（唯一一份） | `src/agent.embedcpu/BgeCpuEmbedder.cs` | 构造注入端口（`BgeCpuEmbedder(model, backend)`，缺省 CPU）；6 个投影全部改走端口；`MatMulBackendName` 供证据 |
| Vulkan 实现 | `src/agent.rover/gpu/VulkanMatMulBackend.cs` | 端口适配 + 形状特化内核缓存 + 入参形状断言；设备/管线生命周期仍交 `VulkanBackend` |
| 内核 | `src/agent.rover/gpu/spirv/Kernels.cs` `MatMulBias(inDim,outDim)` | 4 绑定（W/X/B/Y）；`inDim/outDim` 为**编译期常量**（形状特化，内核内不用 ArrayLength 反推维度）；越界线程 `i ≥ ArrayLength(Y)` 守卫直接返回 |
| 真机入口 | `src/agent.rover/cli/EmbedCli.cs`（`agent.rover embed`） | CPU/Vulkan 同模型同文本逐元素对账；`--selftest` 机器判定；`--device` 负控 |

`agent.embedcpu` 只依赖 `agent.contextgradient`，`agent.rover` 单向引用 `agent.embedcpu`（**无环**）；产品程序集（`agent.host`）**不引入 Silk.NET**（沿用 `agent.csproj` 既有边界：主机侧仅 CLI 引用 Vulkan）—— 故本轮产品侧 AOT 仍为 **IL 警告 0**。

---

## 2. 真机结果（全部为最终二进制产物，非中间版本）

设备：`vkdevice{index=0 name="llvmpipe (LLVM 20.1.2, 256 bits)" type=Cpu api=4211006 vendor=0x10005 compute_family=0 mem_bytes=3837689856}`（lavapipe=**软件 Vulkan ICD**，本机唯一 Vulkan 设备）。

模型：`/home/agentuser/.agentframework/models/bge-q8.gguf`；3 条文本（中/英/混）。

### 2.1 端口确实被使用（防空心判定）

```
port{name=vulkan engine=BgeCpuEmbedder matmul_per_layer=6 layers=4}
portcheck{backend=vulkan dispatch_calls=72 expected=72 match=True}     # 3 文本 × 24
portcheck{backend=vulkan dispatch_calls=216 expected=216 match=True}   # repeat=3
portcheck{backend=vulkan dispatch_calls=864 expected=864 match=True}   # repeat=12
```

判据不是"跑完没报错"，而是**派发次数 == 层数(4)×6×文本数×重复数**：把端口接成装饰（例如只在 CPU 路径上多套一层）会让 `dispatch_calls=0`，该断言必红。

### 2.2 数值对账（CPU 参考 vs Vulkan 真机）

```
parity{text_index=0 dim=512 max_abs_diff=1.341E-007 cos=1.000000000 bits_equal=16/512 sha256_cpu=aaff86e0e8bf15f9 sha256_port=15e70087da138f0f}
parity{text_index=1 dim=512 max_abs_diff=1.639E-007 cos=1.000000000 bits_equal=14/512 sha256_cpu=40e2ceb04ecc4fcc sha256_port=b7e10accec469ac3}
parity{text_index=2 dim=512 max_abs_diff=2.538E-007 cos=1.000000000 bits_equal=12/512 sha256_cpu=093516e79cd7525a sha256_port=415bc271d66a1490}
done{command=embed backend=vulkan mode=compare ok=True verdict=PASS worst_abs_diff=2.538E-007 worst_cos=1.000000000 bits_identical=False dispatch_calls=72}
```

**舍入语义（必须写清，否则是空心断言）**：内核按 `k` **顺序**单精度累加，CPU 端口走 `TensorPrimitives.Dot`（**SIMD 多累加器**，舍入路径不同）⇒ **不逐位相同**（512 维中仅 12~16 维偶然同值），差异量级 = f32 eps（≤2.54e-7），余弦 = 1.000000000。把"逐位一致"写成判据会得到**假红**；把它写成"只看 NaN"又是空心判定 —— 故判据定为 `max|Δ| ≤ 1e-3 ∧ cos ≥ 0.99999`（`--selftest` 严格档），并把 `bits_equal` 一并打印供人核对。

### 2.3 CPU 基准与确定性

```
# CPU 端口自证 (同一判据, 零差异)
done{command=embed backend=cpu mode=compare ok=True verdict=PASS worst_abs_diff=0.000E+000 worst_cos=1.000000000 bits_identical=True}

# Vulkan 重复 3 次: 同端口多次嵌入逐位一致
determinism{pass=1 port=vulkan texts=3 identical=true}
determinism{pass=2 port=vulkan texts=3 identical=true}
```

### 2.4 负控：显式请求 GPU 端口但设备不存在 ⇒ 必须失败，不得静默退回 CPU

```
bgemodel{... backend=vulkan device_index=99 ...}
vkerr{stage=select index=99 devices=1 note=device_index_out_of_range}
done{command=embed backend=vulkan ok=false reason=device_unavailable device=99}   # 退出码 1
```

`TryOpen` 返回 null ⇒ CLI 直接失败退出，**不产出任何嵌入结果**（"静默回退 CPU 冒充 GPU"这条会在此红）。

### 2.5 AOT：原生二进制跑 Vulkan 端口（无 JIT）

```
rover_publish_exit=0 IL_warnings=6 size=3210936
$ /tmp/r393/rover_aot/agent.rover embed --backend vulkan --selftest
vkdevice{index=0 name="llvmpipe (LLVM 20.1.2, 256 bits)" ...}
portcheck{backend=vulkan dispatch_calls=72 expected=72 match=True}
parity{text_index=0 dim=512 max_abs_diff=1.602E-007 cos=1.000000000 bits_equal=12/512 ...}
done{command=embed backend=vulkan mode=compare ok=True verdict=PASS worst_abs_diff=1.995E-007 worst_cos=1.000000000 dispatch_calls=72}
```

即：**NativeAOT 产物直接跑通 Vulkan 计算端口**。6 条 IL 警告全部来自第三方 `Silk.NET.Core.Loader`（IL3000 ×2 / IL3002 ×4，DependencyContext 单文件探测），**真机实测已证其在本平台无害**（设备枚举 + 派发 + 对账全绿）；该结论只对 Linux/原生 libvulkan 成立，已登记为边界（§5）。

产品侧（不含 Vulkan/Silk.NET）：`dotnet publish src/agent.host -c Release -r linux-x64` ⇒ **EXIT=0 / IL 警告 0 / 原生 14.5 MB**，`--help` 正常（`/tmp/r393/aot_host_help.log`）。

---

## 3. 驱动实测约束：循环头不能带条件分支（本轮最贵的发现）

BGE 端口第一版内核：循环头 = `OpLoopMerge` + `OpBranchConditional(cond, 循环体, merge)`。结果 **`vkCreateComputePipelines` 返回 `VK_ERROR_UNKNOWN`**，而自写结构校验器 `SpirvValidator` 判定合法。

用 `/tmp/r393probe`（一次性探针，枚举最小变体）二分：

| 变体 | 构造 | 结果 |
|---|---|---|
| V0 | 纯逐元素 | ✅ |
| V1 | 函数局部变量（Function 存储类） | ✅ |
| V3 | `OpUDiv` | ✅ |
| **A** | 守卫 + 循环，**条件分支在循环头** | ❌ `ErrorUnknown` |
| **B** | 去掉守卫，条件分支仍在循环头 | ❌ |
| **C** | 循环体无缓冲访问（只累加常量） | ❌ |
| **E** | 循环头分支极性反转 | ❌ |
| **D** | **循环头只 `OpLoopMerge` + 无条件跳转，条件判定在独立条件块（glslang 形状）** | ✅ |

判别：**A/B/C/E 全红、D 绿** ⇒ 与守卫、内存访问、分支极性、维度反推全部无关，**唯一变量是控制流形状**。修复即采用 glslang 形状（`Kernels.cs` 内留有该约束的注释与出处）。机检固化：`BgeMatMulPortTests.MatMulBias_含唯一归约循环且循环头无条件分支`（扫描指令流断言 `OpLoopMerge` 之后必须是无条件 `OpBranch`），并带**判别力负控** `MatMulBias_驱动约束检查器有判别力`（把好内核的循环头改回条件分支，检查器必须报 1 处违规）。

> 教训（已入档 §10.4）：**规范合法性 ≠ 目标实现接受性**；定位必须靠最小变体二分 + 真机执行，不能靠读规范推断。

---

## 4. 内存观测：三次改造都没改变斜率 ⇒ 归因驱动，不记为我方泄漏

`agent.rover embed --backend vulkan --compare --repeat R`（R = 1/6/12 ⇒ 派发 72/432/864）：

| 阶段 | RSS 增量（相对 membase） | 我方资源读数 |
|---|---|---|
| 改前（每派发新建管线类资源，且 finally 只回收 buffer/memory） | 斜率 ≈76 KB/派发 | 每次派发泄漏 6 个 VkHandle（代码事实） |
| 改造① 管线类资源按 (内核名,绑定数) 缓存 | **斜率不变** | `_pipes` 缓存，同形状只编译一次 |
| 改造② 设备缓冲按 64 KiB 档位池化 | **斜率不变** | `pool{classes=5 slots=7 leases=3456 reuses=3449}`（864 次派发仅 7 个缓冲，复用率 **99.8%**） |
| 改造③ 命令缓冲常驻 + `ResetCommandPool` | **斜率不变** | 命令缓冲 1 个，全程复用 |

结论（诚实口径）：**我方三类资源（管线类 / 设备缓冲 / 命令缓冲）均已消除逐次分配并由池读数证明有界**；剩余线性增长落在 **lavapipe（软件 Vulkan ICD）内部实现**，**真 GPU 上必须重测**。在真 GPU 复测前：既不把该增长记为我方泄漏，也不声称已解决。三次改造本身仍保留（它们各自消除了句柄泄漏与每派发 SPIR-V 重编译，属真实收益）。

---

## 5. 诚实边界

1. **本机无真 GPU**：`llvmpipe` 是软件实现 ⇒ Vulkan 端口在本机 **比 CPU 慢**（≈588–693 ms/嵌入 vs CPU ≈249–259 ms/嵌入）。**本轮不提出任何性能承诺**；端口的性能结论必须在真 GPU 上重测（判据与命令已给出）。
2. **产品侧尚未接线**：`agent.csproj` 有既存边界"主机侧仅 CLI 引用 Vulkan"⇒ 端口当前由引擎侧（`agent.rover`）提供。若要让 `agent.host` 进程内选 `vulkan`，需把 `VulkanBackend.cs`/`VulkanMatMulBackend.cs` 共享源接进产品并引入 Silk.NET —— 会带入上述 6 条第三方 IL 警告，**须由用户决策**（本报告不擅自破坏既有边界）。
3. **AOT IL 警告**：引擎侧 6 条为第三方库告警（已真机证明无害）；产品侧 0 条（未引入 Silk.NET）。
4. **循环控制流约束**来自本机唯一驱动实现（lavapipe/LLVM 20.1.2）；换驱动/真 GPU 需复跑 `--selftest` 确认。
5. **seq 形状多样性**：本轮文本较短（seq≈20）；长文本（seq→510）只验证了内核形状特化正确性（`512×2048` 变体在探针中数值对账通过），未做端到端长文本对账。

---

## 6. 复现命令

```bash
export PATH="$HOME/.dotnet:$PATH" DOTNET_ROOT="$HOME/.dotnet"
BIN=./src/agent.rover/bin/Release/net10.0/agent.rover

$BIN embed --backend cpu    --selftest                 # CPU 基准（判据: 差异 0、逐位相同）
$BIN embed --backend vulkan --selftest                 # 真机 Vulkan（判据: ≤1e-3 / cos≥0.99999 / 派发 72/72）
$BIN embed --backend vulkan --compare --repeat 12      # 确定性 + 池读数（slots 恒定）
$BIN embed --backend vulkan --device 99 --compare      # 负控: 必须 ok=false 退出码 1

# AOT（引擎侧真跑 + 产品侧不发福）
dotnet publish src/agent.rover/agent.rover.csproj -c Release -r linux-x64 -p:PublishAot=true -o /tmp/aot-r
/tmp/aot-r/agent.rover embed --backend vulkan --selftest
dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/aot-h   # 注意: 不加 -p:PublishAot=true
```

> 踩坑记录：给 `agent.host` 追加命令行 `-p:PublishAot=true` 会**全局传播**到引用工程，命中 `netstandard2.1` 的 `agent.io` ⇒ `error NETSDK1207`。正确做法是**只用 csproj 内置的 `PublishAot=true`**（`agent.host.csproj:16`），命令行不再重复指定。
