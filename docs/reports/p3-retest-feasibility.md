# P3 向量化重测可行性报告（R90，用户指定注意点 5）

## 结论（反转 R58 定论）

**LLamaSharp 0.20.0 + bge-small-zh-v1.5 (q8_0) 本地 embedding 可行**，且代价远低于预期：

| 指标 | 实测值 |
|---|---|
| 模型体积 | **26.4 MB**（q8_0 量化；R58 预估 100MB+ 基于未量化模型，过时） |
| 向量维度 | 512 |
| 单次 embedding 耗时 | **6-21ms**（CPU, threads=2，无 GPU） |
| 加载耗时 | ~1.7s（进程启动一次性） |
| 语义质量 | 相关句 0.682 / 跨语言 0.531 / 无关句 0.177（**区分度 3.9×**） |
| NuGet 包 | LLamaSharp 0.20.0 + LLamaSharp.backend.cpu 0.20.0（nuget.org 直连可拉） |
| 模型分发 | hf-mirror.com 可下（CompendiumLabs/bge-small-zh-v1.5-gguf） |

## 与 R58 结论的差异（诚实复盘）

R58 的"不可行"判据：①glm/deepseek 无 embedding API ②本地 ONNX 100MB+ 违反 AOT/零依赖。
- 判据① 成立但只封死"云 embedding"，未覆盖"本地 embedding"路径（本轮补测）。
- 判据②体积预估过时：GGUF q8_0 量化后 bge-small-zh 仅 26MB，且词面召回实测有"喜欢/不喜欢"语义反转边界。
- LLamaSharp 主包 AOT 兼容性：探针在 JIT 下跑通，**尚未验证 AOT publish**（下一步门槛）。

## 版本坑（重要）

- **LLamaSharp 0.27.0 CPU 后端在本容器 SIGSEGV**（strace 定位：ggml 读 /proc/cpuinfo 后空指针崩溃，
  avx/avx2/avx512/noavx 四变体全崩；glibc 2.39 正常）→ **必须锁 0.20.0**。
- 0.27 的 Vulkan 后端包可安装但容器无 GPU（"No devices found"）→ Vulkan 路线在无 GPU 环境不可用。
- native 库在包内 `LLamaSharpRuntimes/linux-x64/native/avx*/` 非标准 RID 布局，0.20 的
  `backend.cpu` 才走标准 `runtimes/linux-x64/native` 自动复制。

## 建议接入路径（若 AOT 门槛通过）

1. `agent.vectormemory`（已有项目骨架）引 LLamaSharp 0.20.0 + backend.cpu，模型文件放 `data/models/`（gitignored），启动惰性加载。
2. RAG 混合打分追加语义通道：`score = max(score, cos_sim)`，仅当本地模型文件存在时启用（无模型退化为纯词面 = 现状，零回归风险）。
3. 记忆索引落盘向量缓存（复用 R79 JSONL 通道或二进制），避免重复 embedding。

## AOT 门槛验证（实测，R90 补）

| 形态 | 结果 |
|---|---|
| JIT (dotnet run) | ✓ cosine 0.682/0.531/0.177，6-21ms/次，稳定复现 |
| AOT (PublishAot=true) | **publish 编译成功（仅 1×IL3000 single-file 警）但运行 SIGSEGV（稳定复现 139）** |

IL3000 根因：LLamaSharp `NativeLibraryUtils` 依赖 `Assembly.Location`（AOT/single-file 下为空），
native so 子目录探测（avx/avx2/…）失效后 fallback 加载路径错乱。手动布置 `native/avx2/` 布局仍崩
（崩点在 native init，早于任何用户代码输出）→ **AOT 形态不可用**。

## 最终结论（维持 R58 不变，但边界条件更新）

**框架 AOT 红线（零反射/无动态加载）下 P3 本地向量化不可行**；若未来允许 JIT 部署形态或
LLamaSharp 修复 AOT interop（NativeLibraryUtils 改 AppContext.BaseDirectory 探测），bge-small-zh
q8_0（26MB / 512 维 / 6-21ms / 区分度 3.9×）是成熟接入路径 — 探针代码已验证可跑。

词面召回（2-gram + content_hit floor）继续作为主通道；"喜欢/不喜欢"语义反转维持已知接受边界。
