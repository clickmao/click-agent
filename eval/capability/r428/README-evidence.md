# R428 · 同文折叠（排序/去重层）— 真机成对臂证据（**机检生成**，只从 `verdict-r428.json` 转录）

- 判决: **PASS**；判据: {"C1": true, "C2": true, "C3": true, "C4": true, "C5": true, "C6": true, "C7": true, "C2b": true}

- 计划（判据 T0 冻结先于跑测）: `docs/plans/v0.49.0-r428-duplicate-collapse.md`

## 1. 两臂形态自证

| 臂 | 二进制 | sha256 | 说明 |
|---|---|---|---|
| N (pre-fix) | `/tmp/pub_r423/agenthost` | `2d363b6d132b06e2` | R423 已落档治疗臂 = 本轮唯一变量前的形态 |
| T (treated) | `/tmp/pub_r428/agenthost` | `c547b0bec5b8fbf8` | 本轮 diff（同文折叠） |

## 2. 真机读数（stdout 渲染原文，桩侧真值）

| 语料 | 臂 | 命中（按序，呈现 F4） | 折叠标记 |
|---|---|---|---|
| A | N | cli-6bf6dc8d 0.2798 → probe-0914125816-p004 0.1408 → probe-0914125831-p005 0.1408 | — |
| A | T | cli-6bf6dc8d 0.2798 → probe-0914125816-p004 0.1408 | {'probe-0914125816-p004': 1} |
| D | N | r428-d1 0.2284 → r428-d2 0.2284 | — |
| D | T | r428-d1 0.2284 → r428-d2 0.2284 | — |

- 语料 A = `eval/capability/r422/fixture-sessions`（冻结，3 文档；含同文对 p004/p005）；语料 D = 本轮构造（2 文档，**不同文同分**负控）。
- C1 臂身份锚（R423 登记 `T_treated|A`）: `[["cli-6bf6dc8d", 0.2798], ["probe-0914125816-p004", 0.1408], ["probe-0914125831-p005", 0.1408]]`
- C5: 每次查询 `recall_query` = 1、`llm_call` = 0、渲染声明的命中数 == 实际命中行数、语料逐字节未改；语料 A sha: `b9d47da7a95494da`

## 3. 闭式复算（Python 侧独立实现：正文剥空白后逐字符判等）

```
{
  "A_dup_groups": [
    [
      "probe-0914125816-p004",
      "probe-0914125831-p005"
    ]
  ],
  "A_docs": 3,
  "A_keeper_predicted": [
    "probe-0914125816-p004"
  ],
  "A_keeper_observed": [
    "probe-0914125816-p004"
  ],
  "D_dup_groups": [],
  "D_docs": 2,
  "folded_out_ids": [
    "probe-0914125831-p005"
  ],
  "keeper_match": true
}
```

## 4. 外部事实（C6/C7）

```
{
  "unit_tests": {
    "ok": true,
    "passed": 32,
    "failed": 0,
    "cmd": "dotnet test --filter FullyQualifiedName~SessionHistorySearchTests"
  },
  "aot": {
    "ok": true,
    "il_warnings": 0,
    "bytes": 15176432,
    "env_i_selfstart_rc": 0,
    "publish_rc_line": "RC=0"
  }
}
```

## 5. 诚实边界

1. 语料 A 的同文对是**同一内容的两份副本**（R427 已证逐词元相同）⇒ 本轮证明的是**去重层行为**，不是召回质量提升；非同文同分对（语料 D）**不折叠**，规则不误伤。
2. 折叠后 `probe-0914125831-p005` 不再出现在命中列表 —— 信息未丢失（正文逐字符相同），但**该会话 id 不可见**（只计数为 `同文副本+N`）；若将来需要 id 级可追溯，须在 `Hit` 上携带被折叠 id 列表（本轮刻意不做，避免改渲染契约）。
3. `topK` 截断前折叠：命中名额不再被同文副本占用（这是折叠的收益面），但也会**改变**原本会进入 topK 末位的候选 ⇒ 对「列出全部相关会话 id」类需求是行为变更。
4. 未测：真实长会话库（>3 文档）下的内存/时延；跨会话**近同文**（非逐字符相同）不去重；`/recall` 之外的产品路径（本改动只作用于 `Search`/`Render`）。
5. 语料 D 的「同分」由构造保证（同 |Tokens| ∧ 同 tf ∧ 同 df），已由 C4 与单测双证。