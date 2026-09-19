# R577 附带发现 · 全量套件的「种子相关」假红（HashEmbeddingProvider）

日期: 2026-09-19 ｜ 与用户令「用r1 删3b」**无因果**（本文件所述代码本轮未改动）

## 一、读数（同一二进制, `--no-build`, 同一棵树）

| 运行 | 命令 | 结果 |
|---|---|---|
| 全量 #1 | `dotnet test src/agent.tests/agentframework.tests.csproj` | **1909/1910**, RED = `HashEmbeddingUnificationTests.R6_Chinese_NoSpace_Still_Recalls` (`IndexOutOfRangeException` @ `HashEmbeddingProvider.cs:34`) |
| 全量 #2 | 同上 `--no-build`（同 DLL） | **1910/1910 全绿** |
| 定向 ×25 | `--filter FullyQualifiedName~HashEmbeddingUnificationTests --no-build` | **25/25 绿**（5 次 + 20 次两批） |

⇒ 同一份代码、同一个 DLL，**红/绿随进程翻转**。单次读数（绿或红）都是噪声。

## 二、机制（代码级）

`src/agent.vectormemory/HashEmbeddingProvider.cs:31-34`

```csharp
var hash = Math.Abs(token.GetHashCode());
for (int seed = 0; seed < 3; seed++)
    embedding[(hash + seed * 31337) % _dimension] += 1f;   // ← 索引可为负
```

- `hash` 上界 ≈ `int.MaxValue`，`hash + seed*31337`（seed=1/2）**int32 溢出为负数**，
  而 C# 的 `%` 取被除数符号 ⇒ `负 % 384 = 负` ⇒ `IndexOutOfRangeException`。
- `.NET (Core) 起 `string.GetHashCode()` **每进程随机化** ⇒ 是否命中取决于该进程的种子。
  两个进程同 DLL 一红一绿，正是这个机制的可观测后果。
- 断言推论: 该测试属于「同一输入在不同进程可能不同结果」类，**不可作单次判据**。

## 三、建议修法（一行; 未实施, 待裁）

```csharp
// 任一:
embedding[(int)(((uint)(hash + seed * 31337)) % (uint)_dimension)] += 1f;
// 或
var i = (int)(((long)hash + (long)seed * 31337) % _dimension); if (i < 0) i += _dimension; embedding[i] += 1f;
```

## 四、边界（诚实）

- **未修**：超出本轮授权（用户令仅「用r1 删3b」；另有「不许新增夹具和额外开发」令）。
- 影响面: 任何以「全量全绿」为收口判据的轮次，**单次运行**都可能假红/假绿；
  建议收口读数改为 **n≥3 次取全绿**（同仓纪律允许时）或先修此点。
- 未定位项: 该 flake 的历史出现率（本轮首次观测; 25 次隔离复跑 0 红 ⇒ 低频）。
