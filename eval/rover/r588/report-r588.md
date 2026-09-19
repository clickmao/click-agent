# R588 轮志 · 主线同件扩窗轮（第四窗集 w163..w165）+ R587 五项候选并轮收口

- 判定: **rc=1 / FAIL(质量配对未过)**；铁律 11 前置器 `executable_and_correct=False` `acceptable_scoped=False` blocked=['w163/agentD-r1/g1 rc=1 cases=51/58(expect 58) failed=wythoff#43-public,wythoff#44-public,wythoff#45-hidden,wythoff#47-hidden,wythoff#48-hidden,wythoff#49-hidden,wythoff#54-hidden', 'w163/agentD-r2/g1 rc=1 cases=43/58(expect 58) failed=wythoff#43-public,wythoff#44-public,wythoff#45-hidden,wythoff#46-hidden,wythoff#47-hidden,wythoff#48-hidden,wythoff#49-hidden,wythoff#50-hidden,wythoff#51-hidden,wythoff#52-hidden,wythoff#53-hidden,wythoff#54-hidden,wythoff#55-hidden,wythoff#56-hidden,wythoff#57-hidden', 'w164/agentD-r1/g1 rc=1 cases=43/58(expect 58) failed=wythoff#43-public,wythoff#44-public,wythoff#45-hidden,wythoff#46-hidden,wythoff#47-hidden,wythoff#48-hidden,wythoff#49-hidden,wythoff#50-hidden,wythoff#51-hidden,wythoff#52-hidden,wythoff#53-hidden,wythoff#54-hidden,wythoff#55-hidden,wythoff#56-hidden,wythoff#57-hidden', 'w164/agentD-r3/g1 rc=1 cases=47/58(expect 58) failed=wythoff#43-public,wythoff#44-public,wythoff#45-hidden,wythoff#47-hidden,wythoff#48-hidden,wythoff#49-hidden,wythoff#50-hidden,wythoff#52-hidden,wythoff#53-hidden,wythoff#54-hidden,wythoff#56-hidden', 'w165/agentD-r1/g1 rc=1 cases=44/58(expect 58) failed=wythoff#43-public,wythoff#44-public,wythoff#45-hidden,wythoff#46-hidden,wythoff#47-hidden,wythoff#48-hidden,wythoff#49-hidden,wythoff#50-hidden,wythoff#51-hidden,wythoff#52-hidden,wythoff#53-hidden,wythoff#54-hidden,wythoff#55-hidden,wythoff#56-hidden', 'w165/agentD-r2/g1 rc=1 cases=46/58(expect 58) failed=wythoff#43-public,wythoff#44-public,wythoff#45-hidden,wythoff#47-hidden,wythoff#48-hidden,wythoff#49-hidden,wythoff#50-hidden,wythoff#52-hidden,wythoff#54-hidden,wythoff#55-hidden,wythoff#56-hidden,wythoff#57-hidden', 'w165/agentD-r3/g1 rc=1 cases=43/58(expect 58) failed=wythoff#43-public,wythoff#44-public,wythoff#45-hidden,wythoff#46-hidden,wythoff#47-hidden,wythoff#48-hidden,wythoff#49-hidden,wythoff#50-hidden,wythoff#51-hidden,wythoff#52-hidden,wythoff#53-hidden,wythoff#54-hidden,wythoff#55-hidden,wythoff#56-hidden,wythoff#57-hidden', 'w165/codex/g1 rc=1 cases=53/58(expect 58) failed=wythoff#46-hidden,wythoff#51-hidden,wythoff#55-hidden,wythoff#56-hidden,wythoff#57-hidden']
- 配对差(有效窗): {} 中位 **-9.0**（下限 -2）；真值自身失分窗剔除并单列: {'pass': False, 'unreliable': ['w165'], 'truth_all_pass': {'w163': [True], 'w164': [True], 'w165': [False]}}
- 全窗集池化: 9 有效窗, 摆动 15 vs 效应 -7 ⇒ **摆动 > 效应 ⇒ 该轴非承重变量、定案关闭**（符号 {'neg': 7, 'pos': 0, 'zero': 2}, 双侧 p=0.0156）
- 优化前后同列并排 (R587 → R588): 有效窗 2 → 2；配对中位 -6.5 → -9.0；摆动 15 → 15

## KPI 表（同题面/同夹具/同窗内对照）

| 臂 | 回复质量(逐窗/中位/极差) | 调用 | 新算prompt | completion | 命中率(v_all/v_incr) | 步数/轮数 | rc |
|---|---|---|---|---|---|---|---|
| C1(codex 真值) | [58, 58, 53] / 58 / 5 | 66 | 30790 | 37046 | 0.9616 / 0.9705 | [None, None, None] | 1 |
| R588D(产品) | [51, 43, 58, 43, 58, 47, 44, 46, 43] / 46 / 15 | 18 | 4260 | 40447 | 0.9597 / 0.9385 | [13, 7, 14, 13, 7, 7, 7, 7, 7] | 1 |

## 候选台账（R587 遗留五项，全部并入本轮）

- `c1_fourth_window_set` — 做 (w163..w165)
- `c2_timeout_cause` — 做: {'NONCONVERGENT': 3, 'NONCONVERGENT_AT_T10': 5}
- `c3_noartifact_cause` — 做: class={"OK_RC0": 4, "EXHAUSTED": 19, "SELFTEST_UNMET": 3, "NO_ARTIFACT": 1} delta=0
- `c4_subspec_thickening` — 做: 未分类 18→2, 判别力 gap 0.007
- `c5_denominator_policy` — 做: NO_ARTIFACT 计入配对 + 单列 (1/27=3.7%), unreliable 仅留给真值自身失分窗

- 形式门禁: `dotnet test --filter VerificationForm|SkillGeneralization|DevPlanDocRef` ⇒ **14/14 绿 (Failed 0, Passed 14)**; 起手闸 A1/A2 PASS; leak-selfcheck rc=0; 铁律 11 前置器 rc=1 (见上)。

## 诚实边界

- 单窗读数不得作能力结论；摆动 ≥ 效应时该轴非承重变量（本件/本题集范围内）。
- 候选④的子类**判别力 gap ≈ 0**（对照组命中率 0.882 vs 未分类组 0.889）⇒ 只作描述性登记，不改判据、不宣称能力。
- 候选③ 的**字符级**病因未定因（残余已入档）。
- 真值臂本轮出现长命令 120s yield 轮询（codex 侧行为）⇒ 耗时读数只作指示性。

## 证据路径

- `eval/rover/r588/{prereg-r588.json, run_r588.sh, kpi_r588.py, verdict-r588.json, kpi-table-r588.json}`
- `eval/rover/r588/{noartifact-cause-r588.json, timeout-cause-r588.json, subspec-v2-r588.json}`
- `eval/rover/r588/noartifact-denominator-spec-r588.md`
- 台账行: `eval/capability/kpi.jsonl` (round=R588)
