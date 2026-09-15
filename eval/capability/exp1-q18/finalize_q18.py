#!/usr/bin/env python3
"""EXP1-Q18 终验: 把预注册 9 条判据逐条机检并落 verdict_q18.json / evidence_q18.txt。

三态: 达标(True) / 越线(False) / 弃权(None -> n/a, 单列计数, 不记 0)。
"""
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
Q18 = ROOT / "eval/capability/exp1-q18"
F = Q18 / "frozen"
PROV = ROOT / "eval/capability/exp1-q17/archive_field_provenance.py"
Q16V = ROOT / "eval/capability/exp1-q16/verdict_q16.json"
NONSEM = ("probe_version", "run_started_epoch", "run_finished_epoch")


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def load(p):
    return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))


def arm_probe(n):
    return ROOT / f"eval/capability/q18a-{n}/probe_v{n[1:]}.py"


checks = {}


def rec(cid, ok, detail, note=None):
    checks[cid] = {"status": ("达标" if ok is True else "越线" if ok is False else "弃权(n/a)"),
                   "ok": ok, "detail": detail, "note": note}


# ---------- C1 单变量 ----------
b = load(Q18 / "build_q18.json")
rec("C1_单变量", b["ok"] is True,
    {"changed_lines": b["checks"]["changed_line_indices"],
     "src_sha256": b["src_sha256"], "dst_sha256": b["dst_sha256"]},
    "预注册: 恰好 2 行 (版本常量 + 白名单); 实测 changed_line_count=%d" % b["checks"]["changed_line_count"])

# ---------- C2 语义零回归 (冻结语料同源两臂) ----------
a = load(F / "arm_v260/probe_stdout.json")
c = load(F / "arm_v270/probe_stdout.json")
va, vb = a.get("probe_version"), c.get("probe_version")
for k in NONSEM:
    a.pop(k, None)
    c.pop(k, None)
same = json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(c, sort_keys=True, ensure_ascii=False)
rec("C2_语义零回归", same,
    {"probe_version": [va, vb], "ignored_nonsemantic_fields": list(NONSEM),
     "equal_after_strip": same},
    "预注册文本只写了剥离 probe_version; 实测还须剥离 2 个墙钟字段 ⇒ 判据**收窄**(事后白名单), 已单列 checks_posthoc")

# ---------- C3/C4 归档键面与行覆盖 ----------
def scan(p):
    ks, rows = set(), []
    for ln in pathlib.Path(p).read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        r = json.loads(ln)
        rows.append(r)
        ks |= set(r.keys())
    return ks, rows


ka, ra = scan(F / "arm_v260/citations.jsonl")
kb, rb = scan(F / "arm_v270/citations.jsonl")
n_faces_nonempty = sum(1 for r in rb if r.get("symbol_faces"))
n_faces_present = sum(1 for r in rb if "symbol_faces" in r)
n_reloc = sum(1 for r in rb if r.get("relocated_symbol_faces"))
rec("C4_行覆盖", n_faces_present == 921,
    {"rows_with_symbol_faces_present": n_faces_present,
     "rows_with_symbol_faces_nonempty": n_faces_nonempty,
     "rows_with_relocated_symbol_faces": n_reloc,
     "predicted_rows_with_symbol_faces": 921, "rows_total": len(rb),
     "q17_checker_reading_present": ((load(Q18 / "verdict_q18_provenance.json").get("readings") or {})
                                     .get("rows_with_symbol_faces")),
     "early_returns_before_face_assign": ((load(Q18 / "verdict_q18_provenance.json").get("readings") or {})
                                          .get("early_returns_before_face_assign"))},
    "预注册预测 921, 实测 present=%d / nonempty=%d ⇒ **预注册判据被证伪**: 预测模型错"
    "(把「未早退」当成「有 face」的充分条件; 实际 presence 由「行内确有候选符号」等前提决定); "
    "relocated 0 命中与预测一致。**字段存在性(887/997) ≠ 字段非空(488/997) 两个数分开报**"
    % (n_faces_present, n_faces_nonempty))
rec("C3_归档键面", (len(kb) - len(ka) == 1 and sorted(kb - ka) == ["symbol_faces"]),
    {"keys_before": len(ka), "keys_after": len(kb), "added": sorted(kb - ka), "removed": sorted(ka - kb),
     "predicted": "A 24->25, 新增恰为 symbol_faces"},
    "预注册预测 24->25; 实测 %d->%d ⇒ 结构性命中; 绝对数因语料漂移(见 C5 note)与登记值不同属预期" % (len(ka), len(kb)))

# ---------- C5/C9 可重放性 (guard 双臂) ----------
def guard_rows(p):
    d = load(p)
    art = next(iter(d.get("artifacts", {}).values()), {})
    rows = {r["emitted_key"]: r for r in (art.get("C1_replay", {}).get("rows") or [])}
    return d, art, rows


dv, av, rv = guard_rows(Q18 / "verdict_q18_replay.json")
dc, ac, rc = guard_rows(Q18 / "verdict_q18_replay_old.json")
tgt_ok = (rv.get("n_symbol_faces", {}).get("equal") is True
          and rv.get("symbol_face_rungs", {}).get("equal") is True)
nr_ok = (len(av.get("not_replayable") or []) == 2
         and sorted(av.get("not_replayable") or []) == ["stale_like_n", "symbol_occurrences"])
typ_ok = (av.get("not_replayable_typed") or {}) == {
    "stale_like_n": "SELF_REFERENTIAL_CROSS_ARTIFACT", "symbol_occurrences": "PARAM_SCOPE"}
rec("C5_可重放性(结构性)", bool(tgt_ok and nr_ok and typ_ok),
    {"treatment_not_replayable": sorted(av.get("not_replayable") or []),
     "treatment_typed": av.get("not_replayable_typed"),
     "n_symbol_faces_registered_vs_replayed": [rv.get("n_symbol_faces", {}).get("registered"),
                                               rv.get("n_symbol_faces", {}).get("replayed")],
     "symbol_face_rungs_equal": rv.get("symbol_face_rungs", {}).get("equal"),
     "symbol_face_rungs_registered": rv.get("symbol_face_rungs", {}).get("registered"),
     "symbol_face_rungs_replayed": rv.get("symbol_face_rungs", {}).get("replayed"),
     "control_not_replayable": sorted(ac.get("not_replayable") or [])},
    "结构性结论(4->2 + 逐桶可复算)成立; 预注册并列的**登记数值面**子句另立 C5b 单判")

# ---------- C5b 预注册的登记数值面 (语料可比性) ----------
reg_0908 = {"absent": 79, "n/a_kind": 1, "declared_member": 84,
            "noncode_mention": 31, "code_mention": 64, "declared_type": 316}
meas = rv.get("symbol_face_rungs", {}).get("registered") or {}
rec("C5b_登记数值面", meas == reg_0908,
    {"preregistered_buckets": reg_0908, "measured_frozen_corpus": meas,
     "sum_0908": sum(reg_0908.values()), "sum_frozen": sum(meas.values()) or None,
     "rows_0908": 928, "rows_frozen": len(rb)},
    "⇒ 数值面**证伪**: 冻结语料行数 997 ≠ 登记券 928 (同机并行执行体推进 R462 新增源码/文档所致) ⇒ "
    "登记数值与冻结语料读数**不可并列**; 该子句按证伪入档, 不作降级解释")
rec("C9_负控成对", bool(len(ac.get("not_replayable") or []) == 4
                     and (ac.get("not_replayable_typed") or {}).get("n_symbol_faces") == "ARCHIVE_FACE_FIELD_ABSENT"),
    {"control_not_replayable": sorted(ac.get("not_replayable") or []),
     "control_typed": ac.get("not_replayable_typed")},
    "对照臂 = 同语料 + 旧器具 ⇒ 2 枚面字段仍判 ARCHIVE_FACE_FIELD_ABSENT; 两臂仅器具版本一个变量")

# ---------- C6 归因分类位移 (Q17 检查器, 双臂) ----------
prov = {}
for tag, arm in (("v270", "v270"), ("v260", "v260")):
    out = Q18 / f"verdict_q18_provenance{'_old' if tag == 'v260' else ''}.json"
    r = subprocess.run([sys.executable, str(PROV), "--probe", str(arm_probe(arm)),
                        "--archive", str(F / f"arm_{arm}/citations.jsonl"),
                        "--registered", str(F / f"arm_{arm}/probe_stdout.json"),
                        "--q16-verdict", str(Q16V), "--out", str(out)],
                       capture_output=True, text=True, cwd=str(ROOT), timeout=600)
    try:
        d = load(out)
    except Exception as exc:  # noqa: BLE001
        prov[tag] = {"rc": r.returncode, "error": str(exc)[:120], "stderr_tail": (r.stderr or "")[-200:]}
        continue
    rd = d.get("readings") or {}
    prov[tag] = {"rc": r.returncode, "exit_code": d.get("exit_code"),
                 "class_distribution": rd.get("class_distribution"),
                 "class_conserved_sum": rd.get("class_conserved_sum"),
                 "D_size": rd.get("D_size"), "A_size": rd.get("A_size"),
                 "rows_with_symbol_faces": rd.get("rows_with_symbol_faces"),
                 "rows_with_symbol_faces_nonempty": rd.get("rows_with_symbol_faces_nonempty"),
                 "early_returns_before_face_assign": rd.get("early_returns_before_face_assign"),
                 "omitted_fields": rd.get("omitted_fields"),
                 "branch_unhit_fields": rd.get("branch_unhit_fields"),
                 "face_field_class": rd.get("face_field_class"),
                 "relocated_face_field_class": rd.get("relocated_face_field_class")}
pc = ((prov.get("v270") or {}).get("class_distribution") or {})
pc_ok = (pc.get("C_written_and_archived") == 25 and pc.get("C_producer_dump_omission") == 7
         and pc.get("C_dump_producer_branch_unhit") == 3
         and (prov.get("v270") or {}).get("class_conserved_sum") == 35)
rec("C6_分类位移(预注册数值面)", False,
    {"predicted": {"C_written_and_archived": 25, "C_producer_dump_omission": 8,
                   "C_dump_producer_branch_unhit": 3, "C_dump_dead_entry": 0, "C_archive_foreign_key": 0,
                   "conserved_sum": 35},
     "measured_v270": pc, "measured_v260": (prov.get("v260") or {}).get("class_distribution"),
     "v260_D_size": (prov.get("v260") or {}).get("D_size"),
     "v270_D_size": (prov.get("v270") or {}).get("D_size"),
     "v260_omitted_fields": (prov.get("v260") or {}).get("omitted_fields"),
     "v270_omitted_fields": (prov.get("v270") or {}).get("omitted_fields")},
    "预注册写 omission 9->8, 实测 9->**7** ⇒ 数值面**证伪**(推导错误: 键一旦进白名单即**构造性**移出 "
    "omission 类, 不可能留在 omission); 修正后的正确分布单列 C6b")
rec("C6b_分类位移(事后修正)", pc_ok,
    {"corrected_v270": pc, "conserved_sum": (prov.get("v270") or {}).get("class_conserved_sum"),
     "v260_baseline": (prov.get("v260") or {}).get("class_distribution")},
    "事后修正判据: v2.7.0 归档 => archived 25 / omission 7 / branch_unhit 3, Σ=35 守恒, "
    "omitted_fields = [block_id, path_exists, pos_end, pos_start, raw, relocated_lines_ok, "
    "relocated_symbols_absent] (7 枚仍不落盘); 与 C5b 同属 checks_posthoc 族")

# ---------- C7 发现面零变化 ----------
f16 = load(Q16V)
f16_counts = next(iter(f16.get("artifacts", {}).values()), {}).get("counts")
same_findings = (av.get("counts") == ac.get("counts"))
rec("C7_发现面零变化", same_findings,
    {"v270_counts": av.get("counts"), "v260_counts": ac.get("counts"),
     "q16_registered_counts": f16_counts},
    "同语料双臂 findings 逐键相同 ⇒ 本轮 diff 未引入/未消除任何 finding; 与 Q16 登记值的差异属语料漂移, 单列信息项")

# ---------- C8 产物零回归 ----------
before = dict(l.split()[::-1] for l in (Q18 / "baseline_shas_before.txt").read_text().splitlines() if l.strip())
now = {"eval/capability/exp1-q10/probe_v260.py": sha(ROOT / "eval/capability/exp1-q10/probe_v260.py"),
       "eval/capability/exp1-q10/citations.jsonl": sha(ROOT / "eval/capability/exp1-q10/citations.jsonl"),
       "eval/capability/exp1-q10/attribution_q10.json": sha(ROOT / "eval/capability/exp1-q10/attribution_q10.json"),
       "eval/capability/exp1-q10/probe_stdout.json": sha(ROOT / "eval/capability/exp1-q10/probe_stdout.json")}
unchanged = all(before.get(k) == v for k, v in now.items())
rec("C8_产物零回归", unchanged, {"before": before, "now": now},
    "q10 冻结件 sha 逐位不变; 新增产物全部落在 exp1-q18/ 与 q18a-*/ 命名空间")

# ---------- 语料漂移登记 ----------
drift = {"rows_0908_registered": 928, "rows_frozen_corpus": len(rb),
         "face_rungs_registered_0908": {"absent": 79, "n/a_kind": 1, "declared_member": 84,
                                        "noncode_mention": 31, "code_mention": 64, "declared_type": 316, "sum": 575},
         "face_rungs_frozen": rv.get("symbol_face_rungs", {}).get("registered"),
         "face_rungs_frozen_sum": sum((rv.get("symbol_face_rungs", {}).get("registered") or {}).values()) or None,
         "cause": "同机并行执行体在推进 R462 (新增源码/文档) + 本轮 Q16-Q17 之后文档增长 ⇒ 语料行数 928->997",
         "impact": "登记数值面(575 等)与冻结语料读数不可直接并列; 结构性判据(可重放性/分类位移)不受影响"}

n_fail = sum(1 for v in checks.values() if v["ok"] is False)
n_waive = sum(1 for v in checks.values() if v["ok"] is None)
verdict = {"schema": "exp1-q18-verdict/1", "cycle": "EXP1-Q18",
           "instrument": "probe_v270.py (v2.6.0+2 单变量) + unit_axis_guard.py v1.3 (零改动) "
                         "+ archive_field_provenance.py (零改动)",
           "corpus_fingerprint": "bcde4dfc1bcc5939c63bc60148749a2cf0e73f4c046fc953f202dacb1cffdc6",
           "checks": checks, "n_checks": len(checks), "n_fail": n_fail, "n_waived": n_waive,
           "corpus_drift": drift, "provenance": prov,
           "checks_posthoc": [
               "C2 的非语义字段白名单 (run_started_epoch/run_finished_epoch) 为事后补充: 预注册只写了 probe_version",
               "C4 的 921 预测被证伪; 修正模型 = presence 另有「行内确有候选符号」前提 (事后), relocated 0 命中仍成立",
               "C5b = 预注册的登记数值面子句, 因语料漂移判证伪; 结构性判据 C5 达标",
               "C6b = C6 预注册数值 (omission 8) 被证伪后的修正判据 (omission 7), Σ=35 守恒"],
           "exit": 2 if n_fail else 0}
(Q18 / "verdict_q18.json").write_text(json.dumps(verdict, ensure_ascii=False, indent=1), encoding="utf-8")

lines = ["EXP1-Q18 证据 (自检循环, 零 dotnet, 零轮号占用)", "=" * 60,
         "语料: 冻结快照 /tmp/q18_corpus  fingerprint %s" % verdict["corpus_fingerprint"],
         "双臂: eval/capability/q18a-v260 (v2.6.0 对照) / q18a-v270 (v2.7.0 治疗)", ""]
for cid, v in checks.items():
    lines.append(f"[{v['status']}] {cid}  :: {str(v['note'])[:150]}")
lines += ["", "关键读数:",
          "  n_symbol_faces: registered %s / replayed %s (equal=%s)" % (
              rv.get("n_symbol_faces", {}).get("registered"), rv.get("n_symbol_faces", {}).get("replayed"),
              rv.get("n_symbol_faces", {}).get("equal")),
          "  symbol_face_rungs: equal=%s" % rv.get("symbol_face_rungs", {}).get("equal"),
          "  不可重放 对照 %s -> 治疗 %s" % (sorted(ac.get("not_replayable") or []),
                                    sorted(av.get("not_replayable") or [])),
          "  语料漂移: 行数 %s -> %s; face_rungs Σ 575 -> %s" % (
              drift["rows_0908_registered"], drift["rows_frozen_corpus"], drift["face_rungs_frozen_sum"]),
          "", f"n_fail={n_fail} n_waived={n_waive} exit={verdict['exit']}"]
(Q18 / "evidence_q18.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
print("VERDICT_WRITTEN", Q18 / "verdict_q18.json")
