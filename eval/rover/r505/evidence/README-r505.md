# R505 证据一页（主线对照: 外部真值 codex-cli × 本侧 AOT agenthost, 同题集 11 题）

| 批 | rc | codex 整题全对 | codex 调用 | codex tokens | 本侧整题全对 | 本侧调用 | 本侧 tokens |
|---|---|---|---|---|---|---|---|
| a | 0 | 10/11 | 25 | 177172 | 10/11 | 21 | 127623 |
| b | 0 | 9/11 | 33 | 270552 | 11/11 | 18 | 101415 |
| c | 0 | 11/11 | 22 | 154943 | 10/11 | 19 | 80551 |

## 判据（预注册口径）
- H7 质量面: codex 30/33 | 本侧 31/33 | mode 逐题一致 28/33 ⇒ PASS
- H8 调用构成: 本侧逐批调用数 [21, 18, 19] | 均值 19.333333333333332 | 目标 ≤14 ⇒ 未达标 | 归因覆盖 全归位
- H9 跨时间复核: PASS

## 逐题调用构成（本侧, 三批合计）
- m001: 5 次
- m002: 3 次
- m003: 3 次
- m004: 3 次
- p001: 10 次
- p002: 10 次
- p003: 3 次
- p004: 9 次
- p005: 3 次
- p006: 5 次
- p007: 4 次

## 跨时间复核明细
- a/agent: rc=0 replayable=True
- a/codex: rc=0 replayable=True
- b/agent: rc=0 replayable=True
- b/codex: rc=0 replayable=True
- c/agent: rc=0 replayable=True
- c/codex: rc=0 replayable=True

## 归因器二次取数
- a/agent: rc=0 eval/rover/r505/evidence/a/attr-agent-a.json
- b/agent: rc=0 eval/rover/r505/evidence/b/attr-agent-b.json
- c/agent: rc=0 eval/rover/r505/evidence/c/attr-agent-c.json
