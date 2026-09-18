#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R555 入仓: /tmp/r555 运行树 → eval/rover/r555/{snapshots,evidence,readings-r555.jsonl} + 前置器声明。
形状逐字节对齐 R554 (快照 <win>/<armdir>/g1/, report.json rows[arm,tid,side,all_pass,...])。"""
import io, json, os, shutil

REPO = "/home/agentuser/AgentFramework"
R = os.path.join(REPO, "eval/rover/r555")
D = "/tmp/r555"
ARM_DIR = {"A0": "agentR555A0", "A1": "agentR555A1"}
S = json.load(io.open(os.path.join(D, "summary-r555.json"), encoding="utf-8"))
rows = S["rows"]
wins = sorted({r["win"] for r in rows})


def copy_tree(src, dst):
    n = b = 0
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        rel = os.path.relpath(root, src)
        tgt = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(tgt, exist_ok=True)
        for f in files:
            sp = os.path.join(root, f)
            shutil.copy2(sp, os.path.join(tgt, f))
            n += 1
            b += os.path.getsize(sp)
    return n, b


req = []
nonreq = []
art_all = []
for w in wins:
    wd = os.path.join(R, "snapshots", "w%d" % w)
    os.makedirs(wd, exist_ok=True)
    ed = os.path.join(R, "evidence/windows", "w%d" % w)
    os.makedirs(ed, exist_ok=True)
    rep = {"round": "R555", "win": "w%d" % w, "rows": []}
    arts = []
    for arm, adir in ARM_DIR.items():
        r0 = [x for x in rows if x["win"] == w and x["arm"] == arm]
        if not r0:
            continue
        r0 = r0[0]
        src = os.path.join(D, "%s_%d" % (arm, w), "work")
        dst = os.path.join(wd, adir, "g1")
        n, b = copy_tree(src, dst)
        if arm == "A1":
            req.append("w%d/%s" % (w, adir))
        else:
            nonreq.append({"pattern": "w%d/%s" % (w, adir), "reason": "契约 v1 = 对照基线, 非交付配置"})
        rep["rows"].append({"arm": adir, "tid": "g1", "side": "agent",
                            "all_pass": bool(r0["pass"] == r0["total"] and r0["total"] > 0),
                            "cases_pass": r0["pass"], "cases_total": r0["total"],
                            "fails": r0["fails"], "calls": r0["calls_dump"],
                            "new_prompt": r0["miss_sum"], "prompt": r0["prompt_sum"],
                            "completion": r0["completion_sum"], "v_all": r0["v_all"],
                            "rc": r0["rc"], "stage": r0["stage"],
                            "prefix_chars": r0["prefix_chars"], "prefix_sha256": r0["prefix_sha256"],
                            "public_probe": "%s/%s" % (r0["public_probe_failed"], r0["public_probe_total"]),
                            "probe_repairs": r0["probe_repairs"], "exec_repairs": r0["exec_repairs"]})
        arts.append({"arm": adir, "files": n, "bytes": b})
    json.dump(rep, io.open(os.path.join(ed, "report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({"round": "R555", "win": "w%d" % w, "arms": arts}, io.open(os.path.join(ed, "artifacts.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    art_all.append({"win": w, "arms": arts})

with io.open(os.path.join(R, "readings-r555.jsonl"), "w", encoding="utf-8") as fh:
    for r in rows:
        fh.write(json.dumps({"round": "R555", "arm": r["arm"], "win": r["win"], "cases": "%d/%d" % (r["pass"], r["total"]),
                             "fails": r["fails"], "calls": r["calls_dump"], "new_prompt": r["miss_sum"],
                             "prompt": r["prompt_sum"], "completion": r["completion_sum"], "v_all": r["v_all"],
                             "rc": r["rc"], "stage": r["stage"], "prefix_chars": r["prefix_chars"],
                             "probe": [r["public_probe_failed"], r["public_probe_total"]],
                             "probe_repairs": r["probe_repairs"]}, ensure_ascii=False) + "\n")

pre = {"label": "R555", "layout": "project", "taskset": "eval/rover/r555/taskset-r555.json",
       "snapshot_root": "eval/rover/r555/snapshots", "tasks_n": 1, "windows_n": len(wins),
       "rule": "可验收前置(project 布局): 仓内不可变快照 ⇒ 独立物化到全新临时目录 ⇒ python3 -I -B 实跑隐藏用例脚本 ⇒ 逐条机械判对; 自报 all_pass 只作对照不吃",
       "declared_absent": [], "scope_source": "eval/rover/r555/prereg-r555.json", "scope_prereg": True,
       "scope_require": req, "scope_nonrequired": nonreq}
json.dump(pre, io.open(os.path.join(REPO, "eval/rover/r507pre/precondition-r555.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("wins=%s req=%s" % (wins, req))
print("artifacts=%s" % json.dumps(art_all, ensure_ascii=False)[:200])
