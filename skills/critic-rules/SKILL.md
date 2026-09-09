---
name: critic-rules
description: C# 反模式规则知识 (R01-R08) — 生成代码前自查的静态规则镜像 (机器侧 OutputCritic 同源知识, 供 LLM 预判防患)
version: 1.0.0
license: MIT
keywords:
  - 反模式
  - 代码质量
  - C# 优化
  - 堆分配
  - async
  - 自审
regex_patterns:
  - "(写|生成|实现|给).{0,8}(代码|函数|方法|class|类)"
  - "(优化|检查).{0,4}(代码|性能|内存)"
domain_words:
  - csharp
  - C#
  - dotnet
  - .NET
priority: 4
---

# C# 反模式规则 (Critic Rules R01-R08)

> 与运行时 `OutputCritic` (src/agent/critique/OutputCritic.cs) 同源知识镜像。机器侧在代码输出后静态扫描;
> 本 skill 让 LLM 在**生成前自查** (知识前置)。命中 = 已知改进点提醒, 不是"失败"定性 (R318 语义)。
> 每条 = 反模式 → 机制 → 修法 → 正反例。

## R01 循环内堆分配代替取值 ★最易犯

- **反模式**: `foreach (var input in new[] { a.In0, a.In1 })` — 每次迭代堆分配数组, 仅为了取两个栈上字段。
- **机制**: GC 压力 (每次迭代一个短命分配); 语义是"取值稳定", 分配是纯副作用。
- **修法**: `ref var nn = ref g.N[id]; var a0 = g.Resolve(nn.In0); var a1 = g.Resolve(nn.In1);`
- **例外**: 单元素常量数组可豁免; 真正需要集合抽象时用 `stackalloc` 或显式集合。

## R02 字符串 += 进循环

- **反模式**: `report += item.Name + ",";` (for/foreach/while 内)。
- **机制**: 每次 += 产生新 string (不可变), 中间串链 O(n²)。
- **修法**: `StringBuilder`; 少量用 `string.Join` / 收集后 Join。

## R03 async void (非事件处理器)

- **反模式**: `async void Handle() { ... }` (事件之外)。
- **机制**: 异常不可观察 (直接崩进程); 调用方无法 await。
- **修法**: `async Task` + 传播; 仅 UI 事件处理器保留 async void。

## R04 阻塞等待混用 async

- **反模式**: `GetValueAsync().Result` / `.Wait()` 在 async 链中。
- **机制**: sync-over-async → 死锁面 (SynchronizationContext) + 线程池饥饿。
- **修法**: 全链 `async/await`; 库入口用 ValueTask/ConfigureAwait 说明。

## R05 空 catch 吞异常

- **反模式**: `catch (Exception) { }`。
- **机制**: 异常信息蒸发, 调用方无从排查 (与"失败必须透传"铁律冲突)。
- **修法**: 至少日志/打点; 明确豁免理由注释。

## R06 LINQ Count() > 0

- **反模式**: `if (items.Count() > 0)`。
- **机制**: Count() 全枚举; 只需判空。
- **修法**: `items.Any()` (O(1) 短路)。

## R07 浮点 == 直接比较

- **反模式**: `if (d == 0d)` / `a == b` (double/float)。
- **机制**: 二进制表示误差, == 对计算结果几乎必假。
- **修法**: 容差 `Math.Abs(a - b) < eps`; 或定点/有理数域重设计。

## R08 Dispose 型对象未释放

- **反模式**: `var s = new FileStream(...)` 无 using。
- **机制**: 句柄泄漏直至 GC (非确定性); 文件锁残留。
- **修法**: `using` 声明/语句; 工厂内创建需注明所有权转移。

## 使用方式

生成/审查 C# 代码前, 先对照以上 8 条自查; 输出后机器侧 OutputCritic 仍会静态复核 (双保险)。
规则文案变更走代码源 (OutputCritic.cs), 本镜像随版本同步。
