#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R551 入仓: 把三棵运行树(/tmp/r551=on, /tmp/r551_off=off, /tmp/r551s=on2)的**原始物证**
派生成 ① 仓内不可变快照 ② 验收面 evidence/windows/*/{report,artifacts}.json ③ readings-r551.json
④ 命中率(双口径, 复用 hitrate_dual.py) ⑤ 上游契约面可解析性(JSON 尾随内容退化) ⑥ VOID 判定台账。

纪律: 只读 /tmp 运行树; 每个源件记 (bytes, sha256); VOID 窗**不进快照、不进 require**,
但必须在 readings 里可见(rc/stage/产物树文件数) —— 禁把 VOID 当能力读数, 也禁静默丢弃。
"""
import hashlib
import io
import json
import os
import shutil
import sys

REPO = "/home/agentuser/AgentFramework"
HERE = os.path.join(REPO, "eval/rover/r551")
SRC = [("R551b0", "/tmp/r551_off"), ("R551b1", "/tmp/r551_on")]   # 臂标签 = 轮号+轴值(b0=预算关/b1=预算开)
WINS = (7, 8, 9)
TID = "g1"
sys.path.insert(0, HERE)
import hitrate_dual  # noqa: E402


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


def rd(p):
    return json.load(io.open(p, encoding="utf-8-sig"))


def cases_of(run, w):
    p = os.path.join(run, "r1_%d" % w, "cases.txt")
    if not os.path.isfile(p):
        return None
    lines = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
    rows = [x for x in lines if x.startswith("CASE")]
    return {"total": len(rows), "pass": sum(1 for x in rows if "PASS" in x),
            "failed": sorted(x.split()[1] for x in rows if "PASS" not in x)}


def nfiles(d):
    return sum(len(f) for _, _, f in os.walk(d)) if os.path.isdir(d) else 0


def main():
    man = {"round": "R551", "ingested_at": os.popen("date -Is").read().strip(),
           "note": "R551 原始运行树在仓外(/tmp); 本轮按字节复制入仓并把源 (bytes,sha256) 落盘。",
           "sources": {}}
    readings = {"round": "R551", "windows": {}, "void": [], "hit_definition":
                "命中率(双口径, 脚本化) = hitrate_dual.py: v_all=1−Σmiss/Σprompt(含冷启动) / "
                "v_incr=1−miss_last/prompt_last(仅增量); v_prefix_chars 分母为字符 ⇒ 只作口径错示例",
                "hitrate": {}, "dump_json_parseability": {}}
    dumps_sha = {}
    for arm, run in SRC:
        readings["hitrate"][arm] = hitrate_dual.run(os.path.join(run, "adapter"), run, arm, nwin=3, wins=WINS)
        # ⑤ 上游契约面: 逐 dump 的 response.text 可解析性
        import glob
        ok = bad = 0
        det = []
        dumps_sha[arm] = []
        for f in sorted(glob.glob(os.path.join(run, "adapter", "side-agent-*.json"))):
            d = rd(f)
            t = (d.get("response") or {}).get("text") or ""
            try:
                json.loads(t)
                ok += 1
            except Exception as e:
                bad += 1
                det.append({"file": os.path.basename(f), "len": len(t), "err": str(e)[:80]})
            dumps_sha[arm].append({"file": f.replace("/tmp/", ""), "bytes": os.path.getsize(f), "sha256": sha(f)})
        readings["dump_json_parseability"][arm] = {"parseable": ok, "unparseable": bad, "detail": det}
        man["sources"][arm] = {}
        for w in WINS:
            wd = os.path.join(run, "r1_%d" % w)
            tp = os.path.join(wd, "transcript.json")
            if not os.path.isfile(tp):
                continue
            t = rd(tp)
            cs = cases_of(run, w)
            work = os.path.join(wd, "work")
            nf = nfiles(work)
            void = bool(t.get("rc") == 4 or (cs or {}).get("total", 0) == 0 or nf == 0)
            rec = {"rc": t.get("rc"), "stage": t.get("stage"), "calls": t.get("calls"),
                   "prompt_tokens": t.get("prompt_tokens"), "completion_tokens": t.get("completion_tokens"),
                   "cache_hit_tokens": t.get("cache_hit_tokens"), "cache_miss_tokens": t.get("cache_miss_tokens"),
                   "prefix_chars": t.get("prefix_chars"), "task_sha256": t.get("task_sha256"),
                   "public_probe_total": t.get("public_probe_total"), "public_probe_failed": t.get("public_probe_failed"),
                   "exec_repairs": t.get("exec_repairs"), "correctness_asserted": t.get("correctness_asserted"),
                   "probe_repairs": t.get("probe_repairs"), "probe_repair_budget": t.get("probe_repair_budget"),
                   "public_probe_reason": t.get("public_probe_reason"), "repair_rounds": t.get("repair_rounds"),
                   "cases": cs, "work_files": nf, "void": void,
                   "void_reason": ("rc=4 stage=%s" % t.get("stage")) if t.get("rc") == 4 else
                                  ("work_files=0" if nf == 0 else None)}
            readings["windows"].setdefault("w%d" % w, {})[arm] = rec
            man["sources"][arm]["w%d" % w] = [{"file": tp.replace("/tmp/", ""), "bytes": os.path.getsize(tp),
                                               "sha256": sha(tp)}]
            if void:
                readings["void"].append({"arm": arm, "win": "w%d" % w, "rc": t.get("rc"),
                                         "stage": t.get("stage"), "work_files": nf,
                                         "reason": "契约面/空产出 ⇒ 对能力命题零信息量(不删不覆盖)"})
            else:
                dst = os.path.join(HERE, "snapshots", "w%d" % w, "agent%s-%s" % (arm, TID), TID)
                if os.path.isdir(dst):
                    shutil.rmtree(dst)
                shutil.copytree(work, dst)
                man["sources"][arm]["w%d" % w].append({"snapshot": os.path.relpath(dst, REPO),
                                                       "files": nfiles(dst)})
    json.dump(readings, io.open(os.path.join(HERE, "readings-r551.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(man, io.open(os.path.join(HERE, "source-manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(dumps_sha, io.open(os.path.join(HERE, "dumps-sha256.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    # evidence/windows/*: 只为**有快照**的窗写 (VOID 臂不进自报行, 避免 claim 与实测错配)
    for w in WINS:
        wdir = os.path.join(HERE, "evidence/windows", "w%d" % w)
        os.makedirs(wdir, exist_ok=True)
        arms, rows = {}, []
        for arm, _ in SRC:
            rec = readings["windows"].get("w%d" % w, {}).get(arm)
            if not rec or rec["void"]:
                continue
            cs = rec["cases"]
            allp = bool(cs and cs["total"] and cs["pass"] == cs["total"])
            arms["%s-%s" % (arm, TID)] = {"snapshot": "snapshots/w%d/agent%s-%s/%s" % (w, arm, TID, TID),
                                          "all_pass": allp}
            rows.append({"arm": "%s-%s" % (arm, TID), "tid": TID, "side": "agent", "all_pass": allp,
                         "cases_pass": cs["pass"], "cases_total": cs["total"], "hidden_cases": 58,
                         "cases_rc": 0 if allp else 1, "claim_src": "cases.txt(R551 运行树自判)"})
        json.dump({"window": "w%d" % w, "run_dir": "r1_%d (三棵运行树同窗号)" % w, "arms": arms},
                  io.open(os.path.join(wdir, "artifacts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        json.dump({"rows": rows, "note": "自报读数由运行树 cases.txt 派生(非独立重跑); 独立重跑见前置器"},
                  io.open(os.path.join(wdir, "report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # taskset + cases 入仓
    ts = rd(os.path.join(REPO, "eval/rover/r549/taskset-r549.json"))
    ts["round"] = "r551"
    ts["source"] = "eval/rover/r549/taskset-r549.json (g1 单题面, 逐字节同)"
    json.dump(ts, io.open(os.path.join(HERE, "taskset-r551.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    os.makedirs(os.path.join(HERE, "cases"), exist_ok=True)
    src_cases = os.path.join(REPO, "eval/rover/r542/cases/run_cases_r521.py")
    dst_cases = os.path.join(HERE, "cases/run_cases_r521.py")
    shutil.copy2(src_cases, dst_cases)
    print("[入仓] 快照窗=%s" % sorted(os.listdir(os.path.join(HERE, "snapshots"))))
    print("[入仓] cases sha256 %s (源 %s)" % (sha(dst_cases)[:16], sha(src_cases)[:16]))
    for arm, _ in SRC:
        p = readings["dump_json_parseability"][arm]
        h = readings["hitrate"][arm]
        print("  %-9s dump JSON 可解析 %d/不可解析 %d | 逐窗 v_all=%s v_incr=%s" % (
            arm, p["parseable"], p["unparseable"],
            ["%.1f%%" % (100 * r["v_all"]) if r.get("status") == "ok" else "-" for r in h["rows"]],
            ["%.1f%%" % (100 * r["v_incr"]) if r.get("status") == "ok" else "-" for r in h["rows"]]))
    print("[VOID] %d 窗: %s" % (len(readings["void"]),
                              ", ".join("%s/%s(rc=%s)" % (v["arm"], v["win"], v["rc"]) for v in readings["void"])))


if __name__ == "__main__":
    main()
