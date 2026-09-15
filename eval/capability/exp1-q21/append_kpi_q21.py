#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q21 · 把本轮读数**幂等**追加到 eval/capability/kpi.jsonl (按 round 去重)。"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
KPI = ROOT / 'eval/capability/kpi.jsonl'
ROUND = 'EXP1-Q21'

line = {
 "round": ROUND,
 "ts": "2026-09-15T22:35:00+0800",
 "kind": "instrument-input-surface(exp1-L.8候选②后半: 空白/旧行输入面补全)",
 "artifact": ("eval/capability/exp1-q21/{prereg_q21.json,prereg_q21_amendments.json,io_trace.py,tracer_pkg/{q21_filter.py,sitecustomize.py},"
              "derive_inputs_q21.py,derived_inputs_q21.json,register_q21.py,register_q21_report.json,refresh_changed_q21.py,"
              "verify_registry_zeroregress.py,run_l2_face_and_nc.sh,l2_face_runs.txt,verdict_q21.json,"
              "incident_q21_crossworkstream.json,evidence_q21.txt}; eval/capability/instruments.json(18 行全部补 input_surface 语义);"
              "eval/capability/instruments_check.py(输入面语义机检 + 4 注入模式); "
              "eval/capability/{instruments-check.json,instruments-check-drift.json,instruments-check-surface-claim.json,"
              "instruments-check-surface-unknown.json,instruments-check-nc-notapplied.json}; "
              "docs/plans/v0.22.0-exp1-local-index-and-code-graph.md 附录V"),
 "change": ("L.8 候选② 后半只推进一步 = 把「旧行 input_fingerprint 恒为空」升级为**输入面声明 + 审计钩子实测派生**。"
            "手段: sys.addaudithook 跟踪器(父进程 + 经 PYTHONPATH 注入子 python) 实测每条正控命令实际读了什么, "
            "按预注册排除规则分类(台账本体=自指冻结不进指纹/仓外/运行时/版本库内部/跟踪器自身/器具自身/不可解析相对名), "
            "指纹 sha12 全部由文件字节派生并由 GNU sha256sum 交叉。机检侧新增 input_surface∈{external_files,self_contained,"
            "dynamic_corpus,env_only} 语义判据: **空指纹不再默认放行**(self/dynamic 必须有 reason, dynamic 记观察条数; "
            "external 必须非空; 未知值/字段缺失判红)。零产品代码改动, 零 dotnet(对侧 R463 在飞), 不占主线轮号。"),
 "readings": {
  "tracer_selfcheck": {"ok": True, "P2_positive": "5/5", "P3_negative": "成立", "P4_filter": "成立",
                       "P5_attribution": {"rmtree_events": 4, "all_under_subtree": True, "misattributed_to_repo_root": 0,
                                          "unresolved_fd_relative": 5}},
  "derivation": {"targets_n": 12, "undetermined": 0, "hard_fail": [], "external_files": 3, "self_contained": 6,
                 "dynamic_corpus": 3, "dynamic_counts": {"audit.status_gen": 97, "hooks.pre-commit": 98,
                                                         "r446.judge-precheck": 243},
                 "fingerprint_entries": 36, "cross_check_mismatch": 0,
                 "trace_bytes_total_kb": 332, "capped": False},
  "registry_after": {"rows": 18, "surface_declared": 18, "external_files": 9, "self_contained": 6, "dynamic_corpus": 3,
                     "fingerprint_entries": 50, "audit_hook": 12, "prior_round_registration": 6,
                     "reapply_sha_equal": True},
  "zero_regression_registry": {"ids_equal": True, "top_level_keys_equal": True, "removed_keys": [],
                               "value_drift_only_allowed_fills": 3, "other_drift": 0},
  "instrument_refresh": {"row": "l2.instruments-check", "from": "df05321a3d04", "to": "4dba181cd528",
                          "residual_drift": []},
  "l2_face": {"rows_ok": 18, "rows_total": 18, "batch_passed": 17, "batch_fail_cause": "side_effect_gate",
              "side_effects": ["docs/improvements.md", "docs/plans/v715_dev_plan.taskplan.json",
                               "docs/verification-registry.json", "eval/bge/r404/csharp-fusion-replay.json"]},
  "negative_controls": {"drift": {"rc": 1, "fired": True}, "surface_claim": {"rc": 1, "fired": True},
                        "surface_unknown": {"rc": 1, "fired": True}, "surface_missing": {"rc": 1, "fired": True}},
  "instrument_defects_found": {"unbounded_trace_2p1GB": "有界后 332KB (capped=false)",
                               "dir_fd_misattribution": "temp 夹具被错报成仓库根同名文件; 修后错归 0 处"},
  "cross_workstream_incident": {"reverted_tracked_files": 4, "cause": "副作用闸按集合差无法区分并发写者",
                                "recoverable_from_git": False}
 },
 "criterion": ("P1 目标行全覆盖(12/12, undetermined=0) | P2 跟踪器自证 5/5 + 负控 + 过滤器 + 归因 | "
               "P3 分类须派生 | P4 external 行指纹非空且第三方交叉 0 不一致 | P5 self/dynamic 行不得伪造冻结 | "
               "P6 18 行语义机检全 ok | P7 4 类注入负控各判红 | P9 台账既有键零漂移 | P10 不越级 | "
               "**P8 全量面 passed==total ∧ side_effects==[] ⇒ FAIL (行级 18/18 ok, 批次 17/18, 副作用闸 4 条)**"),
 "evidence_level": "L2-static（真机执行 + 审计钩子实测 + 注入矩阵 + 字节派生重算 + 交叉实现校验；零 dotnet ⇒ 不报 L3/L4）",
 "honest": ("① 预注册判据 P8 原样判 FAIL: 4 条 side_effects 经归因实验证明**非本面命令所写**(status_gen --check 与 pre-commit "
            "单独跑均零改写), 而是对侧 R463 在飞写入 —— 但『成因不在本轮 diff』不构成翻绿理由。② 本侧在归因实验中误用 "
            "git checkout 复原了对侧 **4 个 tracked 文件的未提交改动**(registry 行 r463.local-gate-model-switch / improvements "
            "段落 / bge r404 replay / taskplan +9 行): 564 个近 8h 松散对象逐一无命中 ⇒ git 对象库无备份, 只留捕获碎片; 再生路径 = "
            "对侧 settle 步。③ 6 行既往指纹仍标 prior_round_registration(未重推导), 不冒充『全量输入已冻结』。④ dynamic_corpus "
            "3 行为目录级动态语料(97/98/243 条), 结构上不可冻结, 只登记观察条数。⑤ 审计面固有上限: 事件形参不含 dir_fd 的 open "
            "不可解析(只计数) + 非 python 子进程访问不在审计面 ⇒ 输入面是**下界**不是全集。⑥ 形式校验(dotnet)第七轮结转。"
            "⑦ 测量窗口非纯净(对侧臂运行 + llama-server 在场, 本侧未用模型/未跑 dotnet/未占轮号)。"),
 "debt": "(1) 形式校验结转清账(需对侧空闲+内存过闸) | (2) 副作用闸升级为**归因式**(dirty 路径标 PID/命令, 并发写者记 foreign_write 不判红) | (3) 6 行既往指纹用审计钩子重推导 | (4) 对侧 R463 条目由其 settle 步再生 | (5) relocated 面正例语料 / 阶段B 可语言集(各需独立预注册轮次)",
 "next": "① 归因式副作用闸(跟踪器已具备标注能力) → ② 6 行既往指纹重推导 → ③ 形式校验结转清账 → ④ relocated 面正例语料",
 "owner_round": "EXP1-Q21(60m 自检作业; 不占主线轮号)",
 "covers": ["eval/capability/exp1-q21/prereg_q21.json", "eval/capability/exp1-q21/prereg_q21_amendments.json",
            "eval/capability/exp1-q21/io_trace.py", "eval/capability/exp1-q21/tracer_pkg/q21_filter.py",
            "eval/capability/exp1-q21/tracer_pkg/sitecustomize.py", "eval/capability/exp1-q21/tracer_selfcheck.json",
            "eval/capability/exp1-q21/derive_inputs_q21.py", "eval/capability/exp1-q21/derived_inputs_q21.json",
            "eval/capability/exp1-q21/register_q21.py", "eval/capability/exp1-q21/refresh_changed_q21.py",
            "eval/capability/exp1-q21/verify_registry_zeroregress.py",
            "eval/capability/exp1-q21/registry_zeroregress.json", "eval/capability/exp1-q21/l2_face_runs.txt",
            "eval/capability/exp1-q21/verdict_q21.json", "eval/capability/exp1-q21/incident_q21_crossworkstream.json",
            "eval/capability/instruments.json", "eval/capability/instruments_check.py",
            "eval/capability/instruments-check.json", "docs/plans/v0.22.0-exp1-local-index-and-code-graph.md"],
 "negative_control": ("四类注入负控(各写独立命名空间, 不覆盖正控证据): fingerprint drift ⇒ rc=1 DRIFT 命中 | surface-claim(谎报自包含而指纹非空) "
                      "⇒ rc=1 FP_WITHOUT_EXTERNAL_SURFACE | surface-unknown(bogus 值) ⇒ rc=1 BAD/MISSING | surface-missing(字段移除) ⇒ rc=1。"
                      "跟踪器自身负控: 无钩子环境下同一读命令 stdout 仍有内容(读发生但不可见) ⇒ 读数非空心; 过滤器负控: 仓外夹具只计数不进事件面; "
                      "归因护栏: 递归删除事件必须全部落在夹具子树且错归仓库根 = 0 处(本条即本轮抓到的第二个器具缺陷的常驻护栏)。"),
}

existing = []
if KPI.exists():
    for ln in KPI.read_text(encoding='utf-8', errors='replace').splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            existing.append(json.loads(ln))
        except Exception:
            pass
if any(e.get('round') == ROUND for e in existing):
    print('KPI-ALREADY-PRESENT: %s (幂等, 未重复追加)' % ROUND)
else:
    with KPI.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(line, ensure_ascii=False) + '\n')
    print('KPI-APPENDED: %s | lines=%d' % (ROUND, len(existing) + 1))
