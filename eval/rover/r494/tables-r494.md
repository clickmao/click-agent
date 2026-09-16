### 1) 臂矩阵 (机取, 来自 flags-<arm>.json)

| 臂 | turn_gate | repeat_skip | 声明门(意图轴) | **通道轴** | pair_trim | host_sha12 |
|---|---|---|---|---|---|---|
| B | false | off | off | **off** | off | a205c5e34b3a |
| T0 | true | on | on | **off** | on | a205c5e34b3a |
| T1 | true | on | on | **on** | on | a205c5e34b3a |

### 2) 逐臂 KPI (机取, 来自 usage/calls 产物)

| 臂 | 远端调用 | total_tokens | prompt_tokens | cached_tokens | 新算 tokens | completion | 隔离调用 | 隔离调用带工具 | 带工具调用总数 |
|---|---|---|---|---|---|---|---|---|---|
| B | 18 | 86474 | 81134 | 66944 | 14190 | 5340 | 1 | **1** | 18 |
| T0 | 7 | 24728 | 22156 | 15616 | 6540 | 2572 | 1 | **1** | 1 |
| T1 | 7 | 29273 | 23723 | 16768 | 6955 | 5550 | 1 | **0** | 0 |

### 3) 阶梯差 (同窗单变量)

| 对照 | calls | Δcalls | tokens | Δtokens |
|---|---|---|---|---|
| B→T0 | 18→7 | +61.1% | 86474→24728 | +71.4% |
| T0→T1 | 7→7 | +0.0% | 24728→29273 | -18.4% |
| B→T1 | 18→7 | +61.1% | 86474→29273 | +66.2% |

### 4) 跨轮对照 (R493 同网格基线, 仅作竖直参照 —— 禁与 R494 相减)

| R493 臂 | 旗标 | 远端调用 | total_tokens |
|---|---|---|---|
| B(R493) | 全关 | 23 | 101201 |
| R(R493) | gate+skip | 12 | 48562 |
| T(R493) | gate+skip+声明门+pair_trim | 7 | 26962 |

### 5) 实发面断言 (机跑, assert_face_r494.py)

```
[assert-face] arm=B channel=off 远端调用=18 隔离通道调用=1 其中带工具=1 | tool_decl_gate事件=18 带isolated_channel=1
[assert-face] PASS
[assert-face] → ./assert-face-B.json
[assert-face] arm=T0 channel=off 远端调用=7 隔离通道调用=1 其中带工具=1 | tool_decl_gate事件=7 带isolated_channel=1
[assert-face] PASS
[assert-face] → ./assert-face-T0.json
[assert-face] arm=T1 channel=on 远端调用=7 隔离通道调用=1 其中带工具=0 | tool_decl_gate事件=7 带isolated_channel=1
[assert-face] PASS
[assert-face] → ./assert-face-T1.json
```

### 6) 判据器读数 (judge_adv_r494.py, 与 R493 逐字节同)

| 臂 | 对抗族 PASS | endorse | swallowed |
|---|---|---|---|
| B | 2/3 | 1 | 0 |
| T0 | 2/3 | 1 | 0 |
| T1 | 3/3 | 0 | 0 |

### 7) 器具与产物 (机取)


### 8) 能力自检面只读复核 (候选④)

verdict=**FAIL** · 断言 34 · 红 5 · 只读(未写 eval/capability/)

| 面文件 | face | 注入 | total/passed | rc(红项) |
|---|---|---|---|---|
| instruments-check.json | full | - | 23/27 | bind_evidence.check(rc=2),bind_evidence.committed-state(rc=2),exp1q31.only-equivalence(rc=2) |
| instruments-check-scoped.json | scoped | - | 0/1 | exp1q17.archive-field-provenance(rc=2) |
| instruments-check-drift.json | negative-control | drift | 0/1 | exp1q17.archive-field-provenance(rc=0) |
| instruments-check-nc-notapplied.json | None | surface-missing | 0/1 | exp1q4.docref-probe(rc=0) |
| instruments-check-surface-claim.json | None | surface-claim | 0/1 | r444.analyze(rc=0) |
| instruments-check-surface-unknown.json | None | surface-unknown | 0/1 | probe.grade(rc=0) |
