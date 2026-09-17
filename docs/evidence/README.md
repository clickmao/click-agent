# 证据文档结构（RF 版本线起生效）

> 本文是**证据面规范**，不是台账本体。机器台账只有两份，均不在此目录：
> ① `docs/verification-registry.json`（能力 × 验证级 L0–L4，机检器 = `src/agent.tests/VerificationFormTests.cs`）
> ② `eval/capability/kpi.jsonl`（逐轮 KPI 行，键 `round/ts/kind/artifact/change/readings/honest_boundaries/next/owner_round`）

## 1. 目录约定

```
docs/evidence/
  README.md            # 本规范
  INDEX.md             # 人读总索引：版本 → 能力 → KPI → 证据指针 → 验证级
  RF0001/
    KPI.md             # 本版 KPI：口径 / 目标 / 实测 / 逐窗极差 / 未可验收标记
    EVIDENCE.md        # 逐条证据：id | 断言 | 验证级 | 复现命令 | 产物路径+sha | kpi round
```

**RF0001 之前的轮次不补写文档**：其证据仍在 `eval/rover/rNNN/` 与 `docs/reports/`（已归档进 `docs/archive/`），
指针通过 `docs/archive/ARCHIVE-INDEX.md` 找回。禁止回填历史（会引入事后叙事）。

## 2. 三条硬规则

1. **证据本体不进 docs**：产物留在 `eval/**`（受 L3 闸护的轮目录不得搬动）。docs 只写**指针 + sha256 + 复现命令**。
2. **不新建第二本台账**：能力/验证级只登记在 `verification-registry.json`；KPI 读数只写 `kpi.jsonl`。
   证据文档**引用**（`R537`、`EXP1-Q49`）而**不复制**读数 —— 复制即漂移。
3. **每条断言必须绑真实执行**：写进 `EVIDENCE.md` 的每行要能回答「哪条命令、哪个产物、哪次真跑」。
   自报（管道自己打印的字段）不算证据，必须有机检旁证（实发 dump / 产物文件 / 外部判分）。

## 3. 验证级（沿用 `验证形式规范.md`）

| 级 | 含义 | 例 |
|---|---|---|
| L0 | 未验证（仅声明） | 计划里的意图 |
| L1 | 编译/静态 | `dotnet build` 0 错、结构闸 |
| L2 | 单元/集成测试 | 全量 `dotnet test` 1858/1858 |
| L3 | 真机端到端 | AOT 真跑 + 真发 prompt dump |
| L4 | 外部真值对照 | codex-cli 同窗对照（同环境·同输入） |

**降幅类断言最低要求 L3 + 前置器 rc=0**；否则在 `KPI.md` 标「参考（未可验收）」。

## 4. 诚实边界写法

`KPI.md` 必须含「未可验收」小节：逐条写阻塞项（`exec_precondition` rc 与阻塞族）、不可比项（单窗摆动）、未测项。
**「没测到」≠「测过通过」**；rc=8 之类自身返回码不作为正确性证据。
