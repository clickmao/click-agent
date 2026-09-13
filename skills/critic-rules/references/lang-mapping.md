# R01–R08 语言惯用写法映射 (实例)

> 本文件是 `critic-rules` SKILL.md 的**实例章节外置**: 正文只谈机制, 语言/API 细节集中在此。
> 维护约定: 规则语义以机器源 (输出复核器的 Finding 类型) 为准, 本表随版本同步。

| 规则 | C# | Python | Go | Rust | Java |
|---|---|---|---|---|---|
| R01 循环内取值 | `ref` 局部变量 / `CollectionsMarshal` | 直接元组解包 / 局部变量 | 直接索引 | 借用 `&` | 局部变量 |
| R02 字符串拼接 | `StringBuilder` | `"".join(list)` | `strings.Builder` | `String` + `push_str` | `StringBuilder` |
| R03 异步返回空 | 返回 `Task` (非 `async void`) | 返回协程对象 (非 `None`) | 返回 `chan`/`error` | 返回 `Future` | 返回 `CompletableFuture` |
| R04 阻塞等异步 | 全链 `await` | 全链 `await` | 全链 `select`/`chan` | 全链 `.await` | 全链 `join` |
| R05 空捕获 | 记录 + 注释 | 记录 + 注释 | 记录 + 注释 | 记录 + 注释 | 记录 + 注释 |
| R06 计数判空 | `.Any()` / `.Length` | `len()` / `next(it, None)` | `len()` / `,ok` | `is_empty()` | `isEmpty()` |
| R07 浮点比较 | `Math.Abs(a-b) < eps` | `abs(a-b) < eps` | `math.Abs` | `(a-b).abs() < eps` | `Math.abs` |
| R08 资源释放 | `using` | `with` | `defer` | RAII (Drop) | try-with-resources |

## 命中后的处置约定

- 命中 = **已知改进点提醒**, 不是"失败"定性 (避免把风格建议当错误阻断交付)。
- 单一命中不改变任务结论; 多条同类命中指向同一机制时, 按机制修一次即可, 不要逐条打补丁。
