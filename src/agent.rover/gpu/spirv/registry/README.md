# SPIR-V 权威 registry（审计 oracle, 只读不参与执行路径）

本目录存放 Khronos 官方 SPIR-V 语法文件, 用途只有一个: 作为**独立 oracle** 机械核对
`Spv.cs` / `SpirvValidator.cs` 中**手写**的 opcode / 枚举 / 扩展指令号。

## 为什么必须有它

汇编器 (Spv.cs)、结构校验器 (SpirvValidator.cs)、反汇编器 (SpvDisassembler.cs) **共用同一张手写常量表**。
若表中某个号抄错, 三者会**互相印证同一个错误** —— 反汇编看起来"逐字正确", 结构校验报 valid,
而设备实际执行的是另一条指令。

R389-vulkan 实证 (真机, 2026-09-13): `OpUGreaterThanEqual` 抄成 179 (规范 174, 实为 `OpSLessThanEqual`)、
`OpConvertUToF` 抄成 111 (规范 112, 实为 `OpConvertSToF`)。后果: 内核守卫退化成一条带符号比较 ⇒
条件失效 ⇒ 全体 256 个调用都执行 body ⇒ 动态索引写落在 [0,256) 越界区 ⇒
表现为"GPU dispatch 成功但数值全错、动态索引 store 全部不可见"。**只有独立 registry 能发现。**

⇒ 任何新增手写常量都必须能被 `SpvRegistryAudit` 核对, 且 `SpvRegistryAuditTests` 带**负向控制组**
(把常量改错必须红)。审计无判别力 = 未验证。

## 文件来源 (未修改)

| 文件 | 来源 URL | sha256 |
| --- | --- | --- |
| `spirv.core.grammar.json` | `https://raw.githubusercontent.com/KhronosGroup/SPIRV-Headers/main/include/spirv/unified1/spirv.core.grammar.json` | `c125a0fbf6730fde4625fef2618c4f7611ab42edf9b2ad5bb9291002b10bfad3` |
| `extinst.glsl.std.450.grammar.json` | `https://raw.githubusercontent.com/KhronosGroup/SPIRV-Headers/main/include/spirv/unified1/extinst.glsl.std.450.grammar.json` | `5d72e48247569f9b77a17a849db624350abc9d26f7f72b153bbcf15c37238239` |

Copyright: 2014-2024 The Khronos Group Inc. — License: MIT (文件内自带版权头, 原样保留)。
