#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q37 台账行 (幂等): 键集与既有同族行逐键对齐 —— 与 Q36 的 append_kpi_q36.py 同形。"""
import json
import os

P = 'eval/capability/kpi.jsonl'
row = {
    "round": "EXP1-Q37",
    "ts": "2026-09-16T20:52+0800",
    "kind": ("self-check / 面 l2.instruments-check 偶发 rc=1 隔离复跑分诊(同机争用假红) + 面跑前置占用闸 "
             "+ C14 写入归属分类 + depth-3 归档自足(重跑等价) + 自指成员信息项化 + 投影 pin 可比性历史 "
             "+ 登记表尾 LF 契约修复 (60m 自检作业, 不占主线轮号)"),
    "artifact": ("eval/capability/exp1-q37/{precheck_occupancy.sh,occupancy_T10.txt,occupancy_T11.txt,"
                 "occupancy_T11b.txt,triage_q36_t9_rc1.py,triage_q36_t9_rc1.json,evidence/**,"
                 "archive_selfsufficiency_q37.py,archive_selfsufficiency_q37.json,archived_deps_depth3/**,"
                 "pin_history_q37.py,pin_history_q37.json,sync_q37.py,run_face_q37.sh,face_q37_t10.json,"
                 "appendix_al.md}; eval/capability/face_class_count.py; eval/capability/instruments_check.py; "
                 "eval/capability/instruments.json; eval/capability/exp1-q17/archive_field_provenance.py; "
                 "eval/capability/exp1-q31/instruments/only_equivalence_guard.py; docs/verification-registry.json; "
                 "eval/capability/{kpi.jsonl,face-scale-ledger.jsonl}; "
                 "docs/plans/v0.22.0-exp1-local-index-and-code-graph.md (附录 AL)"),
    "change": ("① 面 rc=1 **隔离复跑分诊** (候选①): 判决 CONTENTION_FALSE_RED (L3) —— 内层 rc=2 为**断言红** "
               "(measurement_ok=True / self_dirt=[]) ∧ 同命令隔离复跑 exit_code=0 零红 ∧ T9 窗口内 4 件 "
               "src/**/*.cs 被写 (19:10:53..19:14:16) + 面 census 记录对侧 dotnet publish/ILC 在场 ∧ 源码机取 C14 为"
               "**唯一**负载耦合判据; 新增前置闸 `precheck_occupancy.sh` (宽模式+两次采样+内存门槛+落盘再读+有界等待; "
               "单位 kB→MB 显式换算, 首版 kB 比 MB 门槛恒判空闲已机检住); C14 加 owner_class 归属 "
               "(handwritten/build_artifact, 不改 passed) + FX16/17/18 夹具 ⇒ 器具 selftest checks 15/15 · fixtures 18/18。"
               "② depth-3 **归档自足** (候选②): 65 兜底结点 = 36 归档 (逐件 sha256 读回) + 29 directory_node (闭集理由); "
               "自足率 90/155 → **126/155 = 81.29%**; 承重判据 = 归档优先**重跑等价** (已归档结点 n_refs 与 Q35 现场读数"
               "逐结点差 0) + 负控 2/2 (摘除⇒回落 live / 污染副本⇒报红); **口径修正**: AK.1 ⑤ 的 90/177=50.8% 分母取错 "
               "(177 是 n_distinct, 被扫面是 155), 旧读数显式作废。"
               "③ 自指成员**信息项化** (候选③): 新模块 `face_class_count.py` (判决与计数单一事实源, 自检 6/6) + 清单 "
               "`class=informational ∧ why_informational` (闭集) + 注入负控禁落信息项行 + 面记录 schema /5→/6 "
               "(member_class/passable_*); 面外独立判 = check_committed_state OK (184 行/248 主张/211 blob); "
               "顺修: 唯一 self_writes 恒为 Q33 运行期侧车 (.runtime.json 按设计逐跑变化) ⇒ 纳入 FACE_OUTPUTS。"
               "④ 投影 pin **可比性历史** (候选④): 由 git 逐修订机取 TEST_VECTOR_SHA12 + round/断点声明 ⇒ 修订 4/带向量 3/"
               "断点 2 (Q35 bbd6b93aa9f0→b989a219bcf4; Q36 b989a219bcf4→07ffb38d2500), Q37 未改规则 ⇒ 与 Q36 可比、与 Q35 及以前不可比。"
               "⑤ **附带闭合**: 唯一可判据真红 only-equivalence P1 的根因 = 登记表**丢尾 LF** (R481 契约) ⇒ 序列化通路补 1 B "
               "而外科通路不补 ⇒ 两路径必不等 (A=341104B/B=341103B, 差异在文件末); 归属=写侧, 判据不放宽; 修 = 恢复规范形 "
               "+ 判据加**前提检查** P0_输入规范形 ⇒ 器具 9/9 PASS。"),
    "readings": ("面 (T10, 树 f834137, 起手闸 IDLE 2668MB): 可判据 **24/25** + 信息项 1/2 + 1 项面自身脏项罚分 ⇒ rc=1; "
                 "唯一真红 = only-equivalence P1 (本轮修 + 9/9 复验), 非器具面回归。scoped 复核 (--only 3 成员): "
                 "可判据 1/1 + 信息项 2/2 + side_effects [] + 闸 red=false verdict=clean。"
                 "triage: verdict=CONTENTION_FALSE_RED grade=L3 (s1 rc=1 / s2 inner rc=2 assertion_red=True / "
                 "s3 exit=0 零红 / s4 src .cs 4 件 + publish+ILC 在场 / s5 C14)。归档自足: 155 扫 = 126 归档 + 29 目录, "
                 "等价差 0, 守恒 4/4, 负控 2/2。face_class_count 自检 6/6。pin 历史: 断点 2 (均 declared), 本轮与 Q36 可比。"
                 "only_equivalence_guard 9/9 (P0/P1 双绿)。器具 selftest 15/15+18/18。"
                 "形式门禁: Failed 0 / Passed 14 / Skipped 0 / Total 14 / 791 ms / exit 0。"
                 "台账 face-scale-ledger: round=EXP1-Q37 headroom=2.952 (n_instruments=27, n_commands=60, "
                 "log_bytes=34094506, capped=false, 读回 rows=7 OK)。声明同步 5 处 (2 sha + 2 成员类 + 1 指纹); "
                 "repin r444 (R2E_R2F_EXIT=0); 补尾 LF 后 bind_evidence --check 全绿。"),
    "honest_boundaries": ("① **T11 (干净窗口全量面) 未跑**: 前置闸在对侧 R495 真机臂在飞期间连续两轮判 BUSY "
                          "(常驻服务 n=2 + MemAvailable 1.2–1.4 GB ≪ 2600 MB) ⇒ 本轮面读数 = T10 (含**已修但未在面内复验** "
                          "的 P1 红); scoped 复核 ≠ 全量面等价。② 候选①档位 L3 由三件支撑 (不复发 ∧ 唯一耦合判据 ∧ 窗口内写者), "
                          "内层失败的具体检查项**不可取回** (明细文件被同命令后续运行覆盖 mtime 20:17:10; trace 目录已回收)。"
                          "③ 归档等价的「自足」只在**当前盘面**成立; 29 件目录结点需现场遍历, 已显式登记为不可归档。"
                          "④ 信息项化不改变任何成员真值, 只把「谁进分母」写清; 自指成员真值仍随树态翻转 (面外核验器为准)。"
                          "⑤ 2600 MB 门槛沿用 Q33 登记值 (起手闸, 非测量精度声明)。⑥ 未 push (推送暂停令在效): 本轮本地 commit。"),
    "next": ("① 干净窗口全量面 T11: 断言 side_effects [] ∧ 可判据 25/25 ∧ 信息项 2/2 ∧ rc=0。"
             "② 29 件目录结点的归档形态 (目录清单快照是否足以复算抽取) —— 独立预注册轮。"
             "③ `bind_evidence --apply` 的「补 1 B LF」路径把**契约违反**打成一等可见字段 + 该轮产物标 noncanonical_input。"
             "④ 信息项机制的反向控制进全量面 (注入「信息项+真红混合」模式, 断言面仍判红)。"
             "⑤ 对侧 r494.capability-face-readonly-audit 里那条「P1 仍红(未闭合)」可据本轮读数由其登记轮闭合。"),
    "owner_round": "EXP1-Q37",
}
seen = []
if os.path.isfile(P):
    for line in open(P, encoding='utf-8-sig'):
        if line.strip():
            seen.append(json.loads(line))
keyset = set(seen[-1].keys())
assert keyset == set(row.keys()), '键集漂移: %s vs %s' % (sorted(keyset), sorted(row.keys()))
if any(r.get('round') == row['round'] for r in seen):
    print('IDEMPOTENT: EXP1-Q37 行已存在')
else:
    with open(P, 'a', encoding='utf-8', newline='') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')
    back = [json.loads(l) for l in open(P, encoding='utf-8-sig') if l.strip()]
    print('APPENDED rows=%d (读回 %s)' % (len(back), 'OK' if len(back) == len(seen) + 1 else 'MISMATCH'))
    assert len(back) == len(seen) + 1
