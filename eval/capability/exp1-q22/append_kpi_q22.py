#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q22 · 把本轮读数**幂等**追加到 eval/capability/kpi.jsonl (按 round 去重)。"""
import datetime
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
KPI = ROOT / 'eval/capability/kpi.jsonl'
ROUND = 'EXP1-Q22'

line = {
 "round": ROUND,
 "ts": datetime.datetime.now().astimezone().strftime('%Y-%m-%dT%H:%M:%S%z'),
 "kind": "instrument-side-effect-attribution(exp1-L.8 后续候选①: 归因式副作用闸)",
 "artifact": ("eval/capability/exp1-q22/{prereg_q22.json,side_effect_gate.py,run_controls_q22.py,controls_q22.json,"
              "evidence_q22.txt,run_integration_q22.py,integration_q22.json,refresh_changed_q22.py,"
              "refresh_changed_q22.json,face_prev_q21.json,l2_face_scoped_q22.json,l2_face_scoped_q22.log,"
              "l2_face_nc_q22.txt,nc_drift.log,nc_claim.log,nc_unknown.log,nc_missing.log}; "
              "eval/capability/instruments_check.py(归因式闸接入 + 重入标记 + rc=3 弃权 + schema /4); "
              "eval/capability/instruments.json(l2.instruments-check 行字节派生刷新); "
              "eval/capability/exp1-q22-controls/tracked_fixture.txt(已提交夹具, 供 clean→dirty 正控); "
              "docs/plans/v0.22.0-exp1-local-index-and-code-graph.md 附录W"),
 "change": ("L.8 后续候选① 只推进一步 = 全量面副作用闸从「git status 前后**集合差**」升级为**按写者归因**。"
            "手段: ①归属通道 = 每条本面命令经 `strace -f -y -e trace=<写类系统调用>` 跟踪 (任意语言/全部后代) + "
            "本闸进程 sys.addaudithook (备用); ②佐证通道 = /proc/*/fd 扫持写句柄的外部 pid + 仓内 cwd 普查 (信息项); "
            "③内容通道 = 窗内每个脏路径 sha12 前后快照。四类归属: self_write(判红) / foreign_write(并发写者, 单列不判红) / "
            "pre_existing(窗内内容未变, 单列) / unattributed(内容变化且无法归因 ⇒ 判红 fail-closed), 附守恒式机检; "
            "跟踪通道不可用 ⇒ 检查器 rc=3 (弃权: 既不判绿也不判红)。配套: 脏路径集合改 `-z --untracked-files=all` "
            "(旧模式把未跟踪**目录**折叠成目录路径 ⇒ 路径级归属不可达)。零产品代码改动, 零 dotnet, 不占主线轮号。"),
 "readings": {
  "controls": {"pass": 10, "total": 10, "driver_exit": 0,
               "new_gate": {"C1_self_dirty_before": "self-side-effect 判红; old_gate_delta=[] (漏检)",
                            "C2_foreign_live_fd": "foreign_write 不判红 + live_fd=[pid]; 旧闸假红 1 条",
                            "C2b_self_same_shape": "self_write 判红 (判别器非恒绿, 成对控制)",
                            "C3_pre_existing": "pre_existing 不判红",
                            "C3b_self_repeat_on_dirty": "self_write 判红; old_gate_delta=[] (旧闸盲区)",
                            "C4_foreign_closed_fd": "foreign_write 不判红 (live_fd=[]); 旧闸假红 1 条 = Q21 事故类",
                            "C6_clean_to_dirty_tracked": "self_write 判红 ∧ 复原后 blob 逐字节一致; 旧闸亦判红 (不回归)",
                            "C7_trace_unavailable": "measure-failed (弃权)",
                            "C8_nested_gate_reentrancy": "rc=0 ∧ 无 PTRACE_TRACEME ∧ 继承标记命中 (事后控制)"},
               "conservation": "10/10 控制 classified==expected (38~43 条)"},
  "criteria": {"P1_conservation": True, "P2_self_channel": True, "P3_foreign_channel": True,
               "P4_q21_blind_spot_closed": True, "P5_no_detection_regression": True,
               "P6_whitelist_semantics": True, "P7_measure_failure_visible": True,
               "P8_integration_zero_regress": True, "P9_registry_refresh": True,
               "checks_posthoc": {"P10_nested_gate_reentrancy": True}},
  "integration": {"scoped_face": "6/6 通过", "wall_s": 7.3, "side_effects": [],
                  "attribution": {"self_n": 0, "foreign_n": 0, "pre_existing_n": 39,
                                  "conservation": "39/39", "measurement_ok": True},
                  "trace": {"commands": 14, "events": 11, "raw_events": 227, "raw_paths_n": 184,
                            "log_bytes": 1831377, "capped": False, "unresolved_relative": 0,
                            "channel": "strace+audithook"},
                  "zero_regress": {"shared_ids": 6, "compared_clean": 6, "drift": 0,
                                   "whitelist": {"l2.instruments-check": ["sha12"]},
                                   "uncompared_ids": 12, "prev_batch": "17/18 (side_effects=4 非本面写入)"},
                  "inject_negative_controls": {"drift": 1, "surface_claim": 1, "surface_unknown": 1,
                                               "surface_missing": 1, "note": "各 EXIT=1 机检判红"}},
  "instrument_refresh": {"row": "l2.instruments-check", "from": "4dba181cd528", "to": "27ae9c5a53ce",
                         "intermediate_void": "106b95f844a9", "residual_drift": [], "readback_ok": True,
                         "registry_diff_lines": 2},
  "instrument_defects_found": {"nested_strace_rejected": "PTRACE_TRACEME: Operation not permitted ⇒ 被包裹器具假红 (scoped 5/6); 修=重入标记 ⇒ 6/6",
                               "outer_whitelist_must_mirror": "外层窗口白名单须与被包裹器具写面一致, 否则其合法写点落 self_write (C8 首跑暴露)"}
 },
 "criterion": ("P1 守恒(四类之和==窗末在册脏路径数) | P2 self 通道自证(trace 非空心) | P3 foreign 通道自证 + 成对控制 C2b | "
               "P4 Q21 盲区闭合(旧闸集合差为空而新闸命中) | P5 不回归旧闸检出类(C6 两闸一致红) | P6 白名单语义不变 | "
               "P7 测量失败可见(rc=3 弃权) | P8 集成零回归(6 行逐位 drift=0 ∧ 批次全绿 ∧ 闸 measurement_ok) | "
               "P9 登记刷新(residual_drift=[] ∧ readback_ok) ⇒ 9/9 通过; P10(嵌套重入) 单列 checks_posthoc"),
 "evidence_level": "L2-static（真机执行 + 控制矩阵 10/10 + 注入负控 4/4 + 守恒机检 + 登记字节派生重算；零 dotnet ⇒ 不报 L3/L4）",
 "honest": ("① 形式校验(dotnet)**第八轮结转**: 对侧 R465(probe_latency + llama-server)与 dotnet build 在飞 ⇒ 本侧零 dotnet。"
            "② **全量面未跑**(probe.run_probe 会拉起 llama-server) ⇒ P8 是**子集**零回归, 不是全量绿; 12 行未比对单列。"
            "③ 新模块 side_effect_gate.py(sha12 9e6f893d2846)**暂无独立登记行** —— 加行需与形式校验同轮; 本轮以 l2.instruments-check 行的字节派生刷新承载。"
            "④ 控制里的外国写者由**驱动器**(非本面命令树)启动, 语义等价于并发 agent 进程, 但**非**真实对侧进程(本轮对侧真写入未发生) ⇒ 只证机制, 不证真实场景已复现。"
            "⑤ strace 通道覆盖本面命令全部后代; 走不见于写类系统调用集的路径(如 io_uring 提交)会出现归属空洞(本轮回读 0 例); 父通道只覆盖本闸进程自身 python 写入。"
            "⑥ C7 场景里内容变化路径落 foreign_write 仅因**无法归因**, 该场景 verdict=measure-failed ⇒ 该分类列不得单独引用。"
            "⑦ 测量窗口非纯净(对侧 R465 探针 + dotnet build 在场; 本侧未用模型/未跑 dotnet/未占轮号)。"
            "⑧ 本轮 scoped/负控跑复写了主面产出文件(eval/capability/instruments-check*.json), 已 `git checkout` 复原到 HEAD(其提交态=Q21 全量面读数), 本轮证据留在 eval/capability/exp1-q22/ 副本。"
            "⑨ 控制夹具 fixtures/c1..c7 + probe.txt 为一次性构造, 保留供复跑(未跟踪)。"),
 "debt": ("(1) 形式校验结转清账(需对侧空闲 + 内存过闸) | (2) 全量 18 行面在新闸下复跑(需对侧空闲) ⇒ 把 P8 升级为全量 | "
          "(3) side_effect_gate.py 登记行(与 (1) 同轮) | (4) 附录 V §V.6 遗留: 6 行既往指纹重推导 | "
          "(5) relocated 面正例语料 / 阶段B 可配语言集(各需独立预注册轮次)"),
 "next": "① 形式校验结转清账 → ② 全量面新闸复跑 → ③ 新模块登记行 → ④ 6 行既往指纹重推导 → ⑤ relocated 面正例语料",
 "owner_round": "EXP1-Q22(60m 自检作业; 不占主线轮号)",
 "covers": ["eval/capability/exp1-q22/prereg_q22.json", "eval/capability/exp1-q22/side_effect_gate.py",
            "eval/capability/exp1-q22/run_controls_q22.py", "eval/capability/exp1-q22/controls_q22.json",
            "eval/capability/exp1-q22/evidence_q22.txt", "eval/capability/exp1-q22/run_integration_q22.py",
            "eval/capability/exp1-q22/integration_q22.json", "eval/capability/exp1-q22/refresh_changed_q22.py",
            "eval/capability/exp1-q22/face_prev_q21.json", "eval/capability/exp1-q22/l2_face_scoped_q22.json",
            "eval/capability/instruments_check.py", "eval/capability/instruments.json",
            "eval/capability/exp1-q22-controls/tracked_fixture.txt",
            "docs/plans/v0.22.0-exp1-local-index-and-code-graph.md"],
 "negative_control": ("控制矩阵成对构造: ① self 通道 ⇒ C1/C2b/C3b/C6 判红(含对**已脏路径重复写**的旧闸盲区证明); "
                      "② foreign 通道 ⇒ C2(持句柄, live_fd 带 pid) / C4(写后关句柄, live_fd 空) 不判红, 且同一形态由本侧写则判红(C2b); "
                      "③ 通道不可用 ⇒ C7 measure-failed(弃权, 不判绿); ④ 白名单内写入不判红(C0 探针, 且 raw_events>=1 证通道非空心); "
                      "⑤ 旧闸对比列逐控制给出(old_gate_false_reds / old_gate_missed_self_writes) ⇒ 新闸不是恒绿也不是恒红。"
                      "集成面: 4 类注入负控各 EXIT=1 判红; 与归档全量面同名 6 行逐位零回归; 登记刷新 residual_drift=[]。"),
}

existing = []
if KPI.exists():
    for ln in KPI.read_text(encoding='utf-8').splitlines():
        if ln.strip():
            existing.append(json.loads(ln))
hit = [e for e in existing if e.get('round') == ROUND]
if hit:
    print('ALREADY_PRESENT: %s 已存在 %d 条 ⇒ 不重复追加' % (ROUND, len(hit)))
else:
    with open(KPI, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(line, ensure_ascii=False) + '\n')
    print('APPENDED: %s' % ROUND)
after = [json.loads(l) for l in KPI.read_text(encoding='utf-8').splitlines() if l.strip()]
print('kpi lines: %d; rounds_tail=%s' % (len(after), [r['round'] for r in after[-3:]]))
print('dup_check: %d' % len([r for r in after if r.get('round') == ROUND]))
