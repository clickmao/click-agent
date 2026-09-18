#!/usr/bin/env python3
"""R549 证据固化 + 预注册(先写后跑): 从 R548 运行树的**原始物证**(transcript/cases.txt/中继
usage dump)派生读数与验收面声明, 供 `exec_precondition --round r549` 做独立机检。

不变量: 本脚本只读 /tmp 原始树与仓内快照, 不产生任何远端调用; 每个源文件记 (bytes, sha256)。
"""
import glob
import hashlib
import io
import json
import os

REPO = "/home/agentuser/AgentFramework"
HERE = os.path.join(REPO, "eval/rover/r549")
SRC = {"R548b": "/tmp/r548_c2", "R548base": "/tmp/r548_d"}
TID = "g1"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


def rd(p):
    return json.load(io.open(p, encoding="utf-8-sig"))


def cases_of(d, w):
    p = os.path.join(d, "r1_%d" % w, "cases.txt")
    if not os.path.isfile(p):
        return None, []
    lines = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
    rows = [x for x in lines if x.startswith("CASE")]
    passn = sum(1 for x in rows if "PASS" in x)
    fails = sorted(x.split()[1] for x in rows if "PASS" not in x)
    return {"total": len(rows), "pass": passn, "failed": fails}, rows


def dump_usage(d):
    """中继 usage dump: {(win, call_idx): usage} (dumps 按窗顺序落盘, 每窗 calls 次)。"""
    out = {}
    for f in sorted(glob.glob(os.path.join(d, "adapter", "side-agent-*.json"))):
        j = rd(f)
        u = (j.get("response") or {}).get("usage") or {}
        out.setdefault("_files", []).append({"file": f.replace("/tmp/", ""), "bytes": os.path.getsize(f), "sha256": sha(f)})
        out.setdefault("_u", []).append({k: u.get(k) for k in ("prompt_tokens", "completion_tokens",
                                                 "prompt_cache_hit_tokens", "prompt_cache_miss_tokens",
                                                 "prompt_tokens_details")})
    return out


def main():
    man = {"round": "R549", "purpose": "R548 运行树入仓 + 前置器机检/命中率复核 的源清单",
           "ingested_at": os.popen("date -Is").read().strip(),
           "note": "R548 原始运行树在仓外(/tmp), 本轮按字节复制入仓并把源 (bytes,sha256) 落盘, "
                   "供事后重算 R548 读数; 本轮一切机检读数来自前置器独立重跑, 不采信此处自报。",
           "sources": {}}
    readings = {"round": "R549", "source_round": "R548", "windows": {}, "dumps_sha256": {},
                "hit_definition": "命中率(口径)=1 − 每次新算/前缀, 逐调用取中继 usage.prompt_cache_miss_tokens/前缀"
                                  "(见 docs/reports/r549-*.md 口径节)"}
    for arm, d in SRC.items():
        summ = rd(os.path.join(d, "summary.json")) if os.path.isfile(os.path.join(d, "summary.json")) else {}
        du = dump_usage(d)
        readings["dumps_sha256"][arm] = du["_files"]
        ui = 0
        for w in (1, 2, 3):
            wd = os.path.join(d, "r1_%d" % w)
            tp = os.path.join(wd, "transcript.json")
            if not os.path.isfile(tp):
                continue
            t = rd(tp)
            cs, _ = cases_of(d, w)
            calls = t.get("calls") or 0
            us = du["_u"][ui:ui + calls]
            ui += calls
            man["sources"].setdefault(arm, {})["w%d" % w] = [
                {"file": tp.replace("/tmp/", ""), "bytes": os.path.getsize(tp), "sha256": sha(tp)}]
            readings["windows"].setdefault("w%d" % w, {})[arm] = {
                "tag": t.get("tag"), "rc": t.get("rc"), "stage": t.get("stage"),
                "calls": calls, "prompt_tokens": t.get("prompt_tokens"),
                "completion_tokens": t.get("completion_tokens"),
                "cache_hit_tokens": t.get("cache_hit_tokens"), "cache_miss_tokens": t.get("cache_miss_tokens"),
                "prefix_chars": t.get("prefix_chars"), "task_sha256": t.get("task_sha256"),
                "self_test_unmet": t.get("self_test_unmet"), "correctness_asserted": t.get("correctness_asserted"),
                "public_probe_ran": t.get("public_probe_ran"), "public_probe_failed": t.get("public_probe_failed"),
                "cases": cs, "per_call_usage": us}
    json.dump(readings, io.open(os.path.join(HERE, "readings-r549.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    # 证据窗(自报行, 仅作对照) + 预注册验收面
    for w in (1, 2, 3):
        wdir = os.path.join(REPO, "eval/rover/r549/evidence/windows", "w%d" % w)
        os.makedirs(wdir, exist_ok=True)
        arms, rows = {}, []
        for arm in SRC:
            cs = readings["windows"]["w%d" % w][arm]["cases"]
            r = readings["windows"]["w%d" % w][arm]
            allp = bool(cs and cs["total"] and cs["pass"] == cs["total"])
            arms["%s-%s" % (arm, TID)] = {"snapshot": "snapshots/w%d/agent%s-%s/%s" % (w, arm, TID, TID),
                                         "all_pass": allp}
            rows.append({"arm": "%s-%s" % (arm, TID), "tid": TID, "side": "agent", "all_pass": allp,
                         "cases_pass": cs["pass"], "cases_total": cs["total"], "hidden_cases": cs["total"],
                         "cases_rc": 0 if allp else 1, "claim_src": "cases.txt(R548 运行树自判)"})
        json.dump({"window": "w%d" % w, "run_dir": "%s/r1_%d" % (os.path.basename(SRC["R548b"]), w),
                   "arms": arms}, io.open(os.path.join(wdir, "artifacts.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        json.dump({"rows": rows, "note": "自报读数由 R548 运行树 cases.txt 派生(非本轮重跑), 仅作对照"},
                  io.open(os.path.join(wdir, "report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    req = ["w%d/%s-%s" % (w, a, TID) for w in (1, 2, 3) for a in ("R548b", "R548base")]
    prereg = {"round": "R549", "written_before_run": True,
              "author": "cron R549 (30min beat)",
              "claim": "R548 新契约(生成物 tools/r1gen/contract.py 加厚) 相对旧契约(R548base) 在**同一题面**上: "
                       "①停链窗→0 ②远端调用/token 不升 ③隐藏用例质量不回退; 单变量=契约文本。",
              "acceptance_rule": "铁律11: 本 prereg 落盘**先于**机检跑; 机检 = "
                                 "`python3 eval/rover/r507pre/exec_precondition.py --round r549`; rc≠0 ⇒ "
                                 "R548/R549 一切 token/调用降幅标「参考(未可验收)」, 禁作验收依据。",
              "evidence_scope": {"require": req, "nonrequired": []},
              "pre_registered_families": {"expected_blocking_family": "wythoff",
                                          "reason": "R548 自述残留失败 100% 落 wythoff 家族; 本轮机检要复核该断言"},
              "same_input_gate": {"prompt_sha256": None, "cases_sha256": None,
                                  "note": "两臂逐字节同题面/同用例由 ingest 阶段断言(见 snapshot-manifest.json)"}}
    ts = rd(os.path.join(HERE, "taskset-r549.json"))
    prereg["same_input_gate"]["prompt_sha256"] = ts["tasks"][0].get("prompt_sha256")
    prereg["same_input_gate"]["cases_sha256"] = hashlib.sha256(
        open(os.path.join(HERE, "cases/run_cases_r521.py"), "rb").read()).hexdigest()
    json.dump(prereg, io.open(os.path.join(HERE, "prereg-r549.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(man, io.open(os.path.join(HERE, "source-manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("[证据] 窗数=3 臂=6 预注册=prereg-r549.json(require=%d)" % len(req))
    for w in (1, 2, 3):
        for arm in SRC:
            r = readings["windows"]["w%d" % w][arm]
            print("  w%d %-9s %s 调用=%s prompt=%s miss=%s comp=%s rc=%s stage=%s 失败族=%s" % (
                w, arm, "%d/%d" % (r["cases"]["pass"], r["cases"]["total"]), r["calls"], r["prompt_tokens"],
                r["cache_miss_tokens"], r["completion_tokens"], r["rc"], r["stage"],
                ",".join(sorted({x.split("#")[0] for x in r["cases"]["failed"]})) or "-"))


if __name__ == "__main__":
    main()
