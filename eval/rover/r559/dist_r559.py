#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R559 分布量化 (零远端调用, 只读 R558 冻结落盘件):
 读 /tmp/r558/{w*}/{codex,agentB0,agentB1,agentB2}/g1/{cases.txt,transcript.json}
 + eval/rover/r558/kpi-table-r558.json 的 ledger_check (dump 区段 vs transcript.calls)
 输出: ①族×案例失败分布 ②臂级 stage/steps 台账 ③调用账差额方向 ④max_exec_repair 在位性
只作**分布口径**, 不与 r555-r557 相减。"""
import io, json, os, re, sys, glob, collections

D = "/tmp/r558"
OUT = "/home/agentuser/AgentFramework/eval/rover/r559/dist-r559.json"

def parse_cases(p):
    fam = collections.Counter(); failed = []
    if not os.path.exists(p): return None
    for ln in io.open(p, encoding="utf-8", errors="replace"):
        m = re.match(r"CASE (\w+)#(\d+)-(\w+) (PASS|FAIL)(.*)", ln.strip())
        if not m: continue
        f, idx, vis, verdict, rest = m.groups()
        if verdict == "FAIL":
            fam[f] += 1; failed.append("%s#%s" % (f, idx))
        else:
            fam.setdefault(f, 0)
    return fam, failed

rows = []
for tp in sorted(glob.glob(D + "/w*/agent*/g1/transcript.json")):
    w, arm = tp.split("/")[3], tp.split("/")[4]
    t = json.load(io.open(tp, encoding="utf-8"))
    c = parse_cases(os.path.dirname(tp) + "/cases.txt") or (collections.Counter(), [])
    rows.append({"win": w, "arm": arm, "max_exec_repair": t.get("max_exec_repair"),
                 "exec_repairs": t.get("exec_repairs"), "repair_rounds": t.get("repair_rounds"),
                 "calls": t.get("calls"), "prompt_tokens": t.get("prompt_tokens"),
                 "completion_tokens": t.get("completion_tokens"),
                 "rc": t.get("rc"), "stage": t.get("stage"),
                 "steps_executed": t.get("steps_executed"), "plan_steps_total": t.get("plan_steps_total"),
                 "public_probe_ran": t.get("public_probe_ran"), "public_probe_failed": t.get("public_probe_failed"),
                 "self_test_unmet": t.get("self_test_unmet"),
                 "fam_fail": dict(c[0]), "failed_cases": c[1]})
for tp in sorted(glob.glob(D + "/w*/codex/g1/cases.txt")):
    w = tp.split("/")[3]
    c = parse_cases(tp)
    rows.append({"win": w, "arm": "C1-codex", "fam_fail": dict(c[0]), "failed_cases": c[1]})

# 聚合: 族级
fam_tot = collections.Counter(); fam_fail = collections.Counter()
for r in rows:
    for f, n in r["fam_fail"].items(): fam_fail[f] += n
agg = {"round": "R559", "source": "R558 冻结落盘件 (只读)", "n_rows": len(rows)}
agg["rows"] = rows
# 失败案例频率
cnt = collections.Counter()
for r in rows:
    for cc in r["failed_cases"]: cnt[cc] += 1
agg["case_fail_freq"] = dict(sorted(cnt.items(), key=lambda kv: -kv[1]))
agg["family_fail_total"] = dict(fam_fail)
# 臂级 stage/预算分布
st = collections.Counter((r["arm"], r.get("stage")) for r in rows if r["arm"] != "C1-codex")
agg["stage_by_arm"] = {"%s|%s" % k: v for k, v in sorted(st.items(), key=lambda kv: str(kv[0]))}
# 计划完成度
plan = [(r["win"], r["arm"], r.get("steps_executed"), r.get("plan_steps_total")) for r in rows if r["arm"] != "C1-codex"]
agg["plan_progress"] = plan
agg["plan_incomplete"] = sum(1 for _, _, a, b in plan if isinstance(a, int) and isinstance(b, int) and a < b)
agg["plan_total_n"] = len(plan)
# 契约修复路径是否被进入
agg["repair_rounds_gt0"] = sum(1 for r in rows if r["arm"] != "C1-codex" and (r.get("repair_rounds") or 0) > 0)
agg["exec_repairs_gt0"] = sum(1 for r in rows if r["arm"] != "C1-codex" and (r.get("exec_repairs") or 0) > 0)
agg["max_exec_repair_present"] = sum(1 for r in rows if r["arm"] != "C1-codex" and r.get("max_exec_repair") is not None)
# 调用账 (kpi-table ledger_check)
kt = json.load(io.open("/home/agentuser/AgentFramework/eval/rover/r558/kpi-table-r558.json", encoding="utf-8"))
lc = kt.get("ledger_check") or []
if isinstance(lc, dict):
    lc = [{"key": k, **v} for k, v in lc.items()]
agg["ledger_check_n"] = len(lc)
agg["ledger_diff_nonzero"] = [x for x in lc if (x.get("diff") or 0) != 0]
agg["ledger_diff_ge1"] = sum(1 for x in lc if (x.get("diff") or 0) >= 1)
agg["ledger_diff_le_m1"] = sum(1 for x in lc if (x.get("diff") or 0) <= -1)
io.open(OUT, "w", encoding="utf-8").write(json.dumps(agg, ensure_ascii=False, indent=1))
print("rows", len(rows), "| codex窗口失败合计", sum(len(r['failed_cases']) for r in rows if r['arm']=='C1-codex'))
print("族级失败(18本侧臂+6codex窗):", dict(fam_fail))
print("计划未完成:", agg["plan_incomplete"], "/", agg["plan_total_n"], "| rr>0:", agg["repair_rounds_gt0"], "| exec>0:", agg["exec_repairs_gt0"], "| max_exec_repair在位:", agg["max_exec_repair_present"], "/18")
print("stage:", json.dumps(agg["stage_by_arm"], ensure_ascii=False))
print("ledger n=", agg["ledger_check_n"], "非零:", json.dumps(agg["ledger_diff_nonzero"], ensure_ascii=False), "| transcript>dump:", agg["ledger_diff_ge1"], "| transcript<dump:", agg["ledger_diff_le_m1"])
print("top失败案例:", list(agg["case_fail_freq"].items())[:14])
