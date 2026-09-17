#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q36 台账行 (幂等): 键集与既有同族行逐键对齐 —— 与 Q35 的 append_kpi_q35.py 同形。"""
import json
import os

P = 'eval/capability/kpi.jsonl'
row = {
    "round": "EXP1-Q36",
    "ts": "2026-09-16T19:20+0800",
    "kind": "self-check / 投影规则新模式(drop+drop_by_id, 跨语言同口径) + 不动点达成 + 反证去饱和 + 台账轮号参数化 + depth-3 闭包裁定 + /tmp 遗留进程清理 (60m 自检作业, 不占主线轮号)",
    "artifact": ("eval/capability/exp1-q36/{extend_rules_q36.py,extend_rules_q36b.py,sync_instrument_sha_q36.py,"
                 "run_face_q36.sh,verdict_q36_gate.json}; eval/capability/{face_record_canon.py,projection_rules.json,"
                 "instruments.json}; eval/capability/exp1-q31/instruments/{face_cap_headroom.py,only_equivalence_guard.py,README.md}; "
                 "src/agent.tests/VerificationFormTests.cs; docs/verification-registry.json; "
                 "docs/plans/v0.22.0-exp1-local-index-and-code-graph.md (附录 AK)"),
    "change": ("① 投影规则新增两模式 (Python `face_record_canon` + C# `ProjDigest` 同口径): `drop`=整子树含基数剔除 "
               "(pre_existing 基数实测逐跑增长 51/54/57/66/67/71/72 ⇒ 保留计数=恒不稳), `drop_by_id`=成员级按身份"
               "选择性遮蔽 (自指成员 bind_evidence.{check,committed-state} 真值随树态翻转 ⇒ 不可冻结; 同族未声明成员逐叶保留)。"
               "另补 trace 扫描派生量族 4 条 (commands/events/raw_events/raw_paths_n, 实测同树态 6158→6159)。规则 16→23 条, "
               "跨语言向量 b989a219bcf4 → 07ffb38d2500 (口径断点已登记)。面自检 21/21 → 28/28 (新增 drop/drop_by_id 两侧样例 + "
               "形态拒载三例)。② 不动点: 归档回放 —— 同树态三跑 T1/T2/T3 投影后差异叶 **0** (摘要 da93a845cde0 全同), "
               "T5 与 T7 (同树态、干净窗口) 摘要 **ac43d4336758 逐位相同**; 新跑 T8 与 T9 (同树态) 差异仅剩声明条件项 "
               "(4 条窗口计数) + 1 条行为面翻转 (见诚实边界)。③ `exp1q31.only-equivalence` 反证**去饱和**: 全表 apply 在刚 "
               "repin 完的表上零变更 ⇒ 旧判据恒红无判别力; 修法 = scratch 副本再注入**第二行**待派生锚 ⇒ **8/8 PASS**。"
               "④ `face_cap_headroom.py` 轮号**参数化** (--round; --append 缺轮号 fail-closed rc=3; 幂等键含轮号) ⇒ 跨轮追加不再"
               "把读数记到 Q31 名下。⑤ depth-3 **闭包裁定** (归档 177 结点分类): 155 扫 (archive 90 / **live 兜底 65**) + 21 弃权 "
               "(gone 10 / unreadable 11) ⇒ **归档不自足 (覆盖 90/177 = 50.8%)**, 需现场兜底 65 结点。⑥ /tmp 遗留进程清理: "
               "PID 945082/945094/945253 (stub.py/stub2.py, 自 09-15 存活) 已按 pid 终止 ⇒ external_asset bytes 漂移根因消除。"),
    "readings": ("面 (T8, 树 7e20495, 干净窗口): **25/27** (Q35 为 23/27); 唯一真红 = `bind_evidence.committed-state` "
                 "rc=2 (自指成员: 提交前恒红, 提交后转绿 —— 本轮由 commit #2 收口), 另有 1 项**面自身脏项**罚分 "
                 "(side_effect_attribution.red=true)。投影不动点: 同树态三跑回放差异叶 0; T5/T7 摘要逐位相同; "
                 "T8↔T9 差异 = 4 条窗口计数 + 1 条行为面翻转 (results/16 l2.instruments-check rc 0→1, 见边界)。"
                 "规则 23 条; 向量 07ffb38d2500; `face_record_canon --selftest` 28/28; `only_equivalence_guard` 8/8; "
                 "`face_cap_headroom --selftest` 4/4; 投影 pin r444: 2c324c3f4c83 → (器具派生重取, R2E_R2F_EXIT=0); "
                 "器具 content-sha 同步 2 行 (headroom dac3f65fd6b8→a04b3a56676e; only-equiv 56b918c29a72→f477c8ba8bb4)。"),
    "honest_boundaries": ("① **不动点带条件**: 「同一树态 ∧ 窗口零外来写入 ∧ 本机无 cwd=仓内外来进程」下成立; "
                          "实测 T9 窗口内有**兄弟写者** (前端 R494 会话写 eval/rover/r494/* 与 eval/bge/r404/*) ⇒ 计数族 "
                          "(foreign_writes / old_gate_delta / old_gate_false_reds / census_in_repo_cwd) 非零 ⇒ pin 需重取 "
                          "(已入口径声明 clean_window_condition)。② T9 比 T8 少 1 项: `l2.instruments-check` rc 0→1 "
                          "(墙钟 202.14s → 273.88s, 同机并发负荷) —— 行为面**不遮蔽**故如实暴露; 单独复跑分诊列入下轮候选 "
                          "(不宣称回归)。③ drop_by_id 的例外**写死身份枚举** (2 个自指成员), 不是模式匹配; 遮蔽后 pin 不再"
                          "覆盖这两成员的裁决, 其真值由提交态核验器独立判。④ depth-3 闭包裁定是**对 Q35 归档的再分类** "
                          "(L2/L3), 未做新测量; 结论「归档不自足」依赖 Q35 记录里 scan_source 字段的自报口径。"
                          "⑤ 未 push (推送暂停令在效): 两次本地 commit。"),
    "next": ("① 面 `l2.instruments-check` 的偶发 rc=1 做**隔离复跑分诊** (真缺陷 vs 同机争用假红), 并把「兄弟写者在飞」"
             "写进面跑前的前置闸 (占用核验落盘再读)。② depth-3 归档自足的补法: 把 65 个 live 兜底结点转为归档物 "
             "(或显式登记「不可归档」理由), 再重跑闭包判定。③ 自指成员的真值改由**独立轮**核验并在面里降级为信息项 "
             "(现由 drop_by_id 遮蔽)。④ 遮蔽族扩容后的 pin 历史值与 EXP1-Q35 及以前不可比, 需在报告面标注。"),
    "owner_round": "EXP1-Q36",
}
seen = []
if os.path.isfile(P):
    for line in open(P, encoding='utf-8-sig'):
        if line.strip():
            seen.append(json.loads(line))
keyset = set(seen[-1].keys())
assert keyset == set(row.keys()), '键集漂移: %s vs %s' % (sorted(keyset), sorted(row.keys()))
if any(r.get('round') == row['round'] for r in seen):
    print('IDEMPOTENT: EXP1-Q36 行已存在')
else:
    with open(P, 'a', encoding='utf-8', newline='') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')
    back = [json.loads(l) for l in open(P, encoding='utf-8-sig') if l.strip()]
    print('APPENDED rows=%d (读回 %s)' % (len(back), 'OK' if len(back) == len(seen) + 1 else 'MISMATCH'))
    assert len(back) == len(seen) + 1
