# R428-hold · 循环入口探针 v3 证据 (机检渲染, 勿手改)

- 生成器: `eval/capability/r428-hold/run_hold.py` · 探针 pre sha256 `d7428582ebc8022f` → post sha256 `e52ebb61ee472da4`
- verdict: **PASS** (H1 计划项入账 / H2 不回退 / H3 自检全绿 / H4 前态可复现 / H5 沉积透明)

## 读数

| 项 | pre (HEAD 版本重跑) | post (工作树 v3) |
|---|---|---|
| mode | `tasks` | `tasks` |
| open_count | 2 | 8 |
| 计划项 (expN) 条数 | 0 | 6 |
| 轮次行 (R\d+) 条数 | 2 | 2 |

## post open_items

1. exp1 本地索引/代码引用图: 未开始
2. exp2 menu 问询协议: 未开始
3. exp3 步骤对齐校验: 未开始
4. exp4 工具需求 + 本地脚本: 未开始
5. exp8 产物→skill 蒸馏 + skill 生命周期 + KPI A/B: 未开始（设计已立档）
6. exp5 教训表（role 模块）: **核心已交付(R370)**：`LessonGeneralization`/`LessonTable`/`RoleLe
7. R371: 进行中
8. R370: 进行中

## 判定器自检 (含负控)

- `--selftest`: **selftest: 15/15 passed (new_open=['R901: 接线已交付(R900)；解法级对比进行中', 'R902: 未开始', 'R910: 进行中', 'exp1 夹具计划项 (未开始): 未开始', 'exp3 夹具计划项 (核心已交付 + 自陈欠项): **核心已交付(R1)**：核心齐；欠 前端通路'] legacy_open=['R902: 未开始'])**, rc=0, FAIL=0
- 负控 N3/N4 = 旧行键/旧分类必须判错 (selftest 内部 A/B, 见 `selftest-v3.txt`)
- legacy (v1 逻辑) 跑真机看板: mode=`selfcheck`, open_count=0 ⇒ v1 连 R371/R370 都读不到 (读错列 + 完成标记先过滤)

## 诚实边界

1. 本 tick **不改产品源码、不跑 dotnet、不占轮号** (R428 由 30 分钟节拍作业 9a97763d5fcd 占用中, mtime 18:14)。
2. 探针只改「读得到/判得准」: `open_items` 的 8 条不等于 8 个待办 —— 轮次行 R371/R370 是否沉积、exp1 是否受阻于用户裁决, 仍须读 `other_cells` 与对应计划文档判定 (探针不做机械裁定)。
3. 未登记 `docs/verification-registry.json`: 该改动需当轮立即跑形式校验 (dotnet) ⇒ 与活跃构建窗口冲突, 顺延到活跃体释放后 (同 R402 tick 处置)。

## 复现

```
python3 eval/capability/r428-hold/run_hold.py      # 重跑全部读数并重渲染本文件
python3 scripts/capability_cycle_status.py --selftest
python3 scripts/capability_cycle.py status
```
