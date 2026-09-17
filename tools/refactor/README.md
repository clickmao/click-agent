# tools/refactor — 项目级重构器具 (dev-time only)

> R526「完全重构」实际使用的工具与流水线。**仅开发期使用**：`reftool/` 不在 `agent.sln`、不参与 AOT 产物、
> 不随产品发布（禁反射/AOT 铁律约束的是产品代码，dev 器具不在此列）。

## 一、结构不变式（机检判据）

判据实体：`src/agent.tests/RefactorStructureTests.cs`（5 个 fact = 4 条不变式 + 1 个负控面板）；
同算法的独立机检：`tools/refactor/invariant_check.py`（不依赖 dotnet，可单独跑）。

| 编号 | 不变式 | R526 终读数 |
|---|---|---|
| I1 | 每个 `.cs` 至多 **1 个顶层类型** | 0 违规 / 1054 文件 |
| I2 | 文件名 = 类型名（`<Type>.cs` 或 `<Type>.<片段>.cs`） | 0 违规 |
| I3a | 每个文件必须显式声明命名空间 | 0 违规 |
| I3b | 同一目录内命名空间唯一 | 0 违规 |
| NC | 负控：4 类注入缺陷必红（单类型/文件名/命名空间/目录混用） | 全红 ⇒ 非恒绿 |

豁免（**逐条登记，新违规不豁免**）：`Program.cs`（顶层语句）；`agent.core/userinteraction`（→`agent.userinteraction`）、
`agent.core/subagent`（→`agent.subagent`）—— 收敛计划见 `docs/reports/r526-project-refactor.md` §6。

## 二、器具

- `reftool/` — 基于 Roslyn 语法树的 C# 工具（四种模式）：
  - `report`：列出含 >1 顶层类型的文件
  - `members <file> <Type>`：按源码顺序列出成员（行号 + 语法种类），用于挑 partial 切点
  - `extract [--apply] [--manifest P]`：顶层类型外移为单文件（含 usings/命名空间/块式命名空间包裹；跳过 `file` 作用域类型）
  - `split <file> <Type> 后缀=成员名 [...] [--apply]`：类内按成员边界切 partial；**字段/事件字段/嵌套类型强制留在主文件**（保静态初始值顺序），并做花括号 token 平衡闸
- `invariant_check.py` — I1/I2/I3 独立机检
- `pipeline/` — R526 实际执行顺序（每步后跑 `agent.sln` 构建 + 全量测试，逐步验证）

```
01_extract_types.py        顶层类型单一化 (Roslyn, manifest 可回滚)
02_namespace_normalize.py  命名空间小写归一 + 测试命名空间统一 + 头部 using 去重
03_split_giant_class.py    IndustrialAgentV2 巨类 partial 拆分
04_build_props_centralize.py src/Directory.Build.props + 25 csproj 去重
05_rename_container_files.py 容器文件改名 <Type>.cs
06_test_registry_patches.py / 07_covers_test_paths.py  钉死路径的测试与登记表 covers 同步
```

## 三、实测教训（R526 血泪）

1. **块式命名空间项目不得转 file-scoped**：`src/agent.io` 是 `netstandard2.1` + `LangVersion 8.0` 兼容库（Unity/Xamarin 宿主可引用），
   file-scoped namespace 是 C# 10 特性 ⇒ 该项目 17 个文件必须保持 `namespace X { ... }` 块式。
2. **禁在方法体范围内做 `using` 去重**：按文本去重会删掉方法内 `using var ms = ...` / `using (var doc = ...)`，
   造成 50+ 处 `CS0103`。只允许在 `namespace` 声明之前的头部区去重（`02` 已按此实现）。
3. **partial 拆分的正确性前提**：字段、事件字段、嵌套类型必须留在主文件 —— 否则跨文件静态字段初始化顺序由编译器决定（不确定）。
4. **类型外移必须带命名空间**：只搬类型体而不带文件头 ⇒ 类型掉进全局命名空间 ⇒ CS0101/CS0246 连锁。
5. **改结构后必须同步两类钉死引用**：`covers` 路径（登记表，`Registry_Exists_And_HasNoViolations` 会判死）与「源码扫描型」测试
   （按路径读源码断言字符串）。R526 全部改为「目录级/片段级扫描」或指向新文件。
