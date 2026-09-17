# R396 — 产品侧 Vulkan 端口(去 Silk.NET 依赖, 名字/版本与 Silk.NET 一致)

> 用户令 (逐字): **"不要引入silk.net; 但用的vulkan.dll文件名与版本请和silk.net库一致"**。
> 上轮遗留边界: "产品侧进程内选 vulkan 需引 Silk.NET ⇒ 带 6 条第三方 IL 告警 ⇒ 待用户决策" —— 本轮按用户裁决落地。

## 1. 做了什么

新增产品侧 GPU 工程 `src/agent.gpu` (18th 工程): **零外部包依赖** (不引 Silk.NET),
Vulkan 通过 BCL 的 `NativeLibrary` + **函数指针** (`delegate* unmanaged[Cdecl]<...>`) 自载 —— 零反射 / AOT 安全。

| 文件 | 作用 |
|---|---|
| `src/agent.gpu/VulkanNames.cs` | 加载器名字 + 请求版本口径 (逐字对齐 Silk.NET 2.23.0) |
| `src/agent.gpu/VulkanLoader.cs` | 解析/导出符号; 失败**显式**返回原因码, 绝不静默回退 CPU |
| `src/agent.gpu/VkStructs.cs` | 最小结构/常量子集 (头字段 + Size=1024 留足空间) |
| `src/agent.gpu/VkProbe.cs` | 加载器 → 实例 → 物理设备枚举; 结果**池化复用** (同进程只解析一次) |
| `src/agent.gpu/cli/GpuCli.cs` | 机器可读行 CLI (`probe` / `--negctl`), 输出走注入 TextWriter |
| `eval/vulkan/extract_silknet_loader_names.py` | **取证脚本**: 从包内程序集机械提取名字 oracle |
| `eval/vulkan/crosscheck_vulkaninfo.py` | **跨实现对账**: 与系统 `vulkaninfo` 逐字段比对 |
| `src/agent.tests/VulkanLoaderParityTests.cs` | 6 条机检判据 (见 §3) |

## 2. 名字/版本一致性 —— 取证而非声明

**名字**: 从 `~/.nuget/packages/silk.net.vulkan/2.23.0/lib/netstandard2.0/Silk.NET.Vulkan.dll` 的**元数据**里
机械提取 UTF-16 字符串常量 (实现调用动态加载器时用的正是这些字面量), 记为 oracle:

```
vulkan-1.dll (windows)  |  libvulkan.so.1 (linux, 优先)  |  libvulkan.so (linux, 兜底)  |  libvulkan.dylib (macos)
源资产 sha256 = 5b788c155a9f5e32b9af5097e3e8ef10e9bc6509d7bd2e431b0889d47052f401
oracle: src/agent.gpu/oracle/silknet-vulkan-loader.json
```

**版本** (两层, 都在机检里锁死):
1. **加载器 ABI 主版本** 由 soname 承载 (`libvulkan.so.1`) —— 与 Silk.NET 候选名逐字相同;
2. **请求的 API 版本** = 引擎侧 Silk.NET 路径的 `Vk.MakeVersion(1, 1, 0)` (见 `src/agent.rover/gpu/VulkanBackend.cs`)
   —— 机检直接扫该源码文件断言字面量存在 (反漂移: 引擎改了而我们没改 ⇒ 测试红), 且断言 `ApiVersion == 4198400` / `FormatVersion == "1.1.0"`。
3. 加载器**实际**报告的实例版本 (本机 `1.3.275`) 只打印, 不做硬编码断言。

## 3. 机检判据 (`VulkanLoaderParityTests`, 5/5 通过)

| # | 判据 | 结果 |
|---|---|---|
| ①② | 三平台候选名逐字 == oracle; 包资产在盘时 sha256 必须与 oracle 记录一致 (否则 oracle 过期须重取) | ok |
| ③ | 请求版本与引擎侧 Silk.NET 路径一致 (源码级反漂移 + 数值断言) | ok |
| ④ | **不引入 Silk.NET**: 依赖声明投影检查 (`PackageReference` / `ProjectReference` 名单里不得出现 Silk; 注释不算, 但**声明算**) | ok |
| ⑤ | 负控: 不存在的加载器名必须显式 `not_found` (加载器不能"永远成功") | ok |
| ⑥ | 真机: 加载器/实例/设备可枚举 + **池化复用** (`Probe()` 返回同一实例, `fresh:true` 才重建) | ok |

## 4. 真机证据

**JIT 与 AOT 双形态同一结论**:

```
$ dotnet src/agent.gpu/bin/Release/net10.0/agent.gpu.dll probe          # JIT
$ /tmp/r396/aot/agent.gpu probe                                        # AOT 单文件 (1.19 MB)
vknames{package=Silk.NET.Vulkan version=2.23.0 windows=vulkan-1.dll linux=libvulkan.so.1 linux_fallback=libvulkan.so macos=libvulkan.dylib requested_api=1.1.0}
vkloader{soname=libvulkan.so.1 reason=ok ok=true instance_version=1.3.275 raw=4206867}
vkdevice{index=0 name="llvmpipe (LLVM 20.1.2, 256 bits)" api=1.4.318 driver=104865800 vendor=0x10005 device=0x0 type=cpu}
done{command=probe ok=true devices=1}
```

**AOT 发布**: `dotnet publish -r linux-x64 -p:PublishAot=true` ⇒ **IL 警告 0**; 输出目录只有 `agent.gpu` (+`.dbg`) 与 oracle 目录 —— **无任何托管依赖, 无 Silk.NET 程序集**。

**跨实现对账 (`crosscheck_vulkaninfo.py`, 对 AOT 产物)**:

```
field{gpu=0 field=name    mine=llvmpipe (LLVM 20.1.2, 256 bits) oracle=llvmpipe (LLVM 20.1.2, 256 bits) verdict=ok}
field{gpu=0 field=api     mine=1.4.318   oracle=1.4.318   verdict=ok}
field{gpu=0 field=driver  mine=104865800 oracle=104865800 verdict=ok}
field{gpu=0 field=vendor  mine=65541     oracle=65541     verdict=ok}
field{gpu=0 field=device  mine=0         oracle=0         verdict=ok}
field{gpu=0 field=type    mine=cpu       oracle=cpu       verdict=ok}
crosscheck{devices=1 fields=6 diff=0 verdict=SOUND}
```

**负控 (AOT 形态)**: `probe --negctl` ⇒ `vknegctl{loaded=false reason=not_found(libvulkan-not-a-real-name-xyz.so.9) verdict=ok}` —— 明确失败而非静默回退。

## 5. 诚实边界

1. **计算管线尚未产品化**: 本轮打通的是"加载器/实例/设备枚举" (Stage 1+2)。产品侧**真正的 MatMul 计算路径** (descriptor/pipeline/命令缓冲) 仍是引擎侧 Silk.NET 实现, 未迁到 agent.gpu ⇒ "产品侧 vulkan 计算端口" 尚需 Stage 3。
2. **内存堆解析未做**: 需要 `vkGetPhysicalDeviceMemoryProperties` 的结构对齐 (含 padding), 本机未逐字段对账 ⇒ 留待 Stage 3 与 vulkaninfo 逐值对账后再落。本轮**只断言对账过的字段**。
3. **真 GPU 未验证**: 本机 `/dev/dri/card0` 是 QEMU 模拟的 **Cirrus Logic GD 5446**, 唯一 Vulkan 设备是 **llvmpipe (lavapipe) 软件 ICD** ⇒ 真 GPU 上的端口斜率/性能需外部机器; 现成脚本 (`crosscheck_vulkaninfo.py`) 可直接在真 GPU 机上复跑并给出同一结构化的对账结论。
4. `VkPhysicalDeviceProperties` 用 `Size=1024` + 只声明头字段 —— 头部偏移 (0/4/8/12/16/20) 已由 vulkaninfo 交叉验证, 但**结构尾部字段未声明**; 若后续要用 `limits`, 必须重新对账偏移。
5. oracle 依赖本机 nuget 缓存中的包资产做溯源复算; 资产缺失时该子断言降级为显式 warn (名字断言仍生效), 不是静默跳过。

## 6. 下轮候选

1. **Stage 3**: 产品侧计算端口 —— 复用引擎侧 SPIR-V 内核, 与 CPU 路径 `--compare` 数值对账 (沿用 R393 的 72/72 dispatch / cos=1.0 口径)。
2. 内存堆解析 + 与 vulkaninfo 逐值对账。
3. 真 GPU 机器上复跑 `crosscheck_vulkaninfo.py` 与内存斜率 A/B。
