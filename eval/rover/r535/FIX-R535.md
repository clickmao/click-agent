# R535 缺陷与修复记录 (2026-09-18)

## 0. 一句话
**R1 结构化管道的首次真跑在冒烟就 fail-closed 报红(`rc=4`)**: 根因是**契约渲染器只渲染顶层 enum**,
`schema` 里声明的嵌套枚举(`entities[].kind` / `plan[].tool`)**从未进入 prompt** ⇒ 模型只能自造取值,
而校验器按同一 schema 的 enum 杀 ⇒ **契约与校验器不同源**。修复走**机械重生成**(禁手工漂移), 并加了一条
可机检的回归闸。修后: 冒烟 `rc=0`, `t1`(不挂 role) 30/30 · `m1` 30/30 · `g1` 58/58。

## 1. 症状 (实测, 非推断)
首次 `run_r535.sh` 在 §3.5 接线冒烟中止:
```
冒烟: cli_rc=4  "rc": 4   (transcript stage=contract)
reply: ... "entities":[{"kind":"path",...},{"kind":"language",...},
               {"kind":"expected_stdout","value":"42"}] ...
R1 结构化管道 … rc=4
```
`transcript.reason` = `契约未过 (errors=1)`, 校验器报 `entities[2].kind 非法/缺失`。

## 2. 根因 (可复现, 两处互证)
- `src/agent/contract/StructuredContract.cs` 的 schema 里 `entities` 的 `items.properties.kind`
  **是**枚举 `[path, symbol, command, value, language]`;
- 但 `contract.render_schema_text()`(原型 `/tmp/fable-r1/contract.py`, C# 由 `gen_csharp.py` 机械生成)
  **只渲染顶层 enum**, 对嵌套属性只渲染 `子字段必填: kind, value` —— **取值域没渲染**。
  ⇒ 线上前缀里没有 `kind` 的合法取值, 模型看到 `entities` 只能说"我猜" (它猜了 `expected_stdout`, 因为
  计划里确有一个 `expect_stdout` 字段), 校验器按 enum 一票否决 ⇒ 管道 fail-closed **空转**。

## 3. 修复 (机械同源, 禁手工改字)
| # | 改动 | 文件 |
|---|---|---|
| ① | 渲染器增 `_nested_enums()`: 把**子对象枚举**渲染成 `；子字段取值: kind ∈ path\|symbol\|command\|value\|language`(对 `plan[].tool` 同理) | `gen/contract.py` (原型) → 重生成 C# |
| ② | 校验器错误消息改为**从 `EntityKindEnum` 派生**(单一取值源): `kind 非法/缺失 (合法: path\|symbol\|command\|value\|language)` | 同上 |
| ③ | 新增回归闸 `Contract_Renders_Every_Enum_Declared_In_Schema`: 枚举片段表由生成器**从 SCHEMA 递归抽出**(禁手工维护), 逐字断言必须出现在契约段与前缀; 带**负控**(抹掉片段 ⇒ 断言必红) | `src/agent.tests/StructuredContractTests.cs` |
| ④ | 把 R533 只手改在 C# 里的 `ExecRepairMessage` **补回生成器** —— 否则下次重生成即静默丢功能(本轮实测踩到, 已回滚后重做) | `gen/gen_csharp.py` |

**pin 上移(声明式)**: 前缀 `3,889` 字符 / `58e2df67…` → **`3,972` 字符 / `c40809b3…`** ——
改的是生成器, 前缀字面量与 `PrefixChars/PrefixSha256Pinned` 由重生成产出, 非手工编辑。

## 4. 证据
- 生成物 diff 面: `StructuredContract.cs`(SchemaText 2 行 + 错误消息 1 行) · `StructuredPrompt.cs`(前缀 2 行 + pin 2 值) · `StructuredContractTests.cs`(+18 行), **无其它文件变动**。
- 机械一致性机检: 3 个枚举片段在 `render_schema_text()` 与 `PREFIX` 中**均逐字出现**(Python 侧独立复算)。
- 测试: 全量 **1789/1789 绿**(修前 2 红: 本闸首版片段形制写错 + 1 例 `FrontendAskSameConnTests` 连接超时, 重跑即过)。
- AOT: `/tmp/pub_r535b/agenthost` sha256 `715f3df9…` · 15,733,520 B · **IL 警告 0**。
- 修后真跑: 冒烟 `rc=0`; `R1nr/t1` 30/30 · `R1r/m1` 30/30 · `R1r/g1` 58/58(见 `POST-R535.md`)。

## 5. 未闭合 (转入 R536 候选)
- 挂 role 的 `R1r-t1` 两次补全均 `"plan":[]` ⇒ `rc=4` · 0/30(role 挂载**当前为负作用**)。
- 不挂 role 的 `R1nr-t1` 产物 30/30 但管道 `rc=5`(`expect_stdout_exhausted`) ⇒ **产物正确与管道 rc 不同步**。
