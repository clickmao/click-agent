#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R553 入仓 + 判据重钉: 结构=逐字节复用 ingest_r552.py, 唯一差异 = **哪个口径是「预注册口径」**。

R552: 预注册口径 = 旧规则 (rc==4 ∨ 无产物 ∨ 无用例 ∨ 上游退化率>0.25) ⇒ 三臂有效窗 0/2/2 (n<3 ⇒ J2 不可判)
R553: 预注册口径 = **新规则** (仅『无产物(work_files=0)』或『无用例可判分(cases.total=0)』)
      rc / stage / 上游退化率 全部**降为 hygiene 字段** (依据 = R552 §4 实测反例, 已在 R553 预注册里事前写明)

产出:
  ① eval/rover/r553/{snapshots,evidence/windows,readings-r553.json,source-manifest.json}
  ② eval/rover/r553/readings-r552-retro.json —— **追溯回算**: 用新规则重读 R552 已落盘的 24 窗(零远端调用,
     只读, 不写 R552 的任何文件; 两口径并列, 禁相减、禁替代 R552 已公布读数)
  ③ voidrule_selfcheck.json —— 新规则判据有牙的负向控制(4 个真样本格 + 旧/新规则差值的正控)

纪律: 只读 /tmp 运行树; 每个源件记 (bytes, sha256); 真 VOID 窗不建窗目录、不进快照、不进 require。
"""
import glob
import hashlib
import io
import json
import os
import shutil
import sys

REPO = "/home/agentuser/AgentFramework"
HERE = os.path.join(REPO, "eval/rover/r553")
TID = "g1"
sys.path.insert(0, os.path.join(REPO, "eval/rover/r552"))
import hitrate_dual  # noqa: E402  (复用 R552 既有器具, 不新增命中率实现)

SRC_R553 = [("R553b0", "/tmp/r553v1_b0", (60, 61, 62)),
            ("R553b1", "/tmp/r553v1_b1", (63, 64, 65)),
            ("R553b2", "/tmp/r553v1_b2", (66, 67, 68))]
SRC_R552 = [("R552b0", "/tmp/r552v2_b0", (30, 31, 32, 39, 40, 41, 49, 50, 51)),
            ("R552b1", "/tmp/r552v2_b1", (33, 34, 35, 43, 44, 45, 52, 53, 54)),
            ("R552b2", "/tmp/r552v2_b2", (36, 37, 38, 46, 47, 48, 55, 56, 57))]


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
    rows = [x for x in io.open(p, encoding="utf-8", errors="replace").read().splitlines() if x.startswith("CASE")]
    return {"total": len(rows), "pass": sum(1 for x in rows if "PASS" in x),
            "failed": sorted(x.split()[1] for x in rows if "PASS" not in x)}


def nfiles(d):
    return sum(len(f) for _, _, f in os.walk(d)) if os.path.isdir(d) else 0


def void_new(rc, total, nf, rate, thr_up):
    """R553 预注册口径: 只有『无产物』或『无用例可判分』判 VOID。"""
    if total == 0:
        return True, "no_cases_judgeable"
    if nf == 0:
        return True, "no_artifacts_on_disk"
    return False, None


def void_old(rc, total, nf, rate, thr_up):
    """R552 预注册口径(保留为并列对照): rc==4 ∨ 无产物 ∨ 无用例 ∨ 上游退化率>0.25。"""
    if rc == 4:
        return True, "rc=4_contract"
    if total == 0:
        return True, "no_cases"
    if nf == 0:
        return True, "no_artifacts"
    if rate is not None and rate > thr_up:
        return True, "upstream_degraded rate=%s" % rate
    return False, None


def voidrule_selfcheck(thr_up=0.25):
    """判据有牙(铁律 9): 用 R552 的**真实窗读数格**做控制 —— 负控必须翻面, 且必须显示新旧规则差值。"""
    samples = [
        {"id": "N1_no_artifacts", "rc": 4, "total": 0, "work_files": 0, "rate": 0.5, "want_new": True},
        {"id": "N2_no_cases", "rc": 0, "total": 0, "work_files": 12, "rate": 0.0, "want_new": True},
        {"id": "N3_rc4_with_artifacts(R552 w43)", "rc": 4, "total": 45, "work_files": 12, "rate": 0.0, "want_new": False},
        {"id": "N4_rate0333_with_artifacts(R552 w38)", "rc": 0, "total": 58, "work_files": 12, "rate": 0.3333, "want_new": False},
        {"id": "P1_clean", "rc": 0, "total": 58, "work_files": 12, "rate": 0.0, "want_new": False},
    ]
    res = {"rule_new": "VOID ⇔ (work_files==0) or (cases.total==0); rc/stage/上游退化率=hygiene",
           "rule_old": "VOID ⇔ (rc==4) or (total==0) or (work_files==0) or (rate>%s)" % thr_up,
           "controls": {}}
    teeth = True
    delta = []
    for s in samples:
        gn, _ = void_new(s["rc"], s["total"], s["work_files"], s["rate"], thr_up)
        go, _ = void_old(s["rc"], s["total"], s["work_files"], s["rate"], thr_up)
        ok = gn == s["want_new"]
        teeth = teeth and ok
        if gn != go:
            delta.append(s["id"])
        res["controls"][s["id"]] = {"want_new": s["want_new"], "got_new": gn, "got_old": go, "ok": ok}
    res["delta_cases"] = delta
    res["has_teeth"] = bool(teeth)
    res["delta_note"] = ("旧规则在 %s 上把**已产出可判分产物**的窗判成 VOID(过宽); "
                         "新规则据此重钉 ⇒ 有效窗数分母改变 (用户令: 只改读数格, 不改质量定义式)" % delta)
    io.open(os.path.join(HERE, "voidrule_selfcheck.json"), "w", encoding="utf-8").write(
        json.dumps(res, ensure_ascii=False, indent=1))
    return res


def ingest(src, tag, write_snapshot, thr_up=0.25):
    readings = {"round": tag, "windows": {}, "void": [],
                "hit_definition": "命中率(双口径, 复用 eval/rover/r552/hitrate_dual.py): "
                                  "v_all=1−Σmiss/Σprompt(含冷启动) / v_incr=1−miss_last/prompt_last(仅增量); 跨轮/跨窗禁相减",
                "void_rule": "R553 预注册口径 = 仅『无产物/无用例可判分』判 VOID(新旧两口径逐窗并列)",
                "hitrate": {}, "dump_json_parseability": {}, "upstream_gate": {}, "precheck": {}}
    man = {"round": tag, "ingested_at": os.popen("date -Is").read().strip(),
           "note": "运行树在仓外; 按字节复制入仓并落盘源 (bytes,sha256)。写快照=%s" % write_snapshot,
           "binary_sha256": "e2fdab87b03b3f9ddae1628471b30b6165c07923e5924d77fbf111d24dd5c27b",
           "sources": {}}
    for arm, run, wins in src:
        if not os.path.isdir(run):
            continue
        readings["hitrate"][arm] = hitrate_dual.run(os.path.join(run, "adapter"), run, arm, nwin=3, wins=wins)
        ok = bad = 0
        det = []
        for f in sorted(glob.glob(os.path.join(run, "adapter", "side-agent-*.json"))):
            t = (rd(f).get("response") or {}).get("text") or ""
            try:
                json.loads(t); ok += 1
            except Exception as e:
                bad += 1; det.append({"file": os.path.basename(f), "len": len(t), "err": str(e)[:80]})
        readings["dump_json_parseability"][arm] = {"parseable": ok, "unparseable": bad, "detail": det}
        readings["upstream_gate"][arm] = {}
        man["sources"][arm] = {}
        for w in wins:
            wd = os.path.join(run, "r1_%d" % w)
            tp = os.path.join(wd, "transcript.json")
            pc = os.path.join(run, "precheck-%d.json" % w)
            if os.path.isfile(pc):
                readings["precheck"]["%s/w%d" % (arm, w)] = rd(pc)
            if not os.path.isfile(tp):
                continue
            t = rd(tp)
            cs = cases_of(run, w)
            work = os.path.join(wd, "work")
            nf = nfiles(work)
            vp = os.path.join(run, "voidchk-%d.json" % w)
            uc = rd(vp) if os.path.isfile(vp) else {}
            up = {k: uc.get(k) for k in ("dumps_in_window", "unparseable", "rate", "void_upstream")}
            readings["upstream_gate"][arm]["w%d" % w] = up
            vn, rn = void_new(t.get("rc"), (cs or {}).get("total", 0), nf, uc.get("rate"), thr_up)
            vo, ro = void_old(t.get("rc"), (cs or {}).get("total", 0), nf, uc.get("rate"), thr_up)
            rec = {"rc": t.get("rc"), "stage": t.get("stage"), "calls": t.get("calls"),
                   "prompt_tokens": t.get("prompt_tokens"), "completion_tokens": t.get("completion_tokens"),
                   "cache_hit_tokens": t.get("cache_hit_tokens"), "cache_miss_tokens": t.get("cache_miss_tokens"),
                   "prefix_chars": t.get("prefix_chars"), "task_sha256": t.get("task_sha256"),
                   "public_probe_total": t.get("public_probe_total"), "public_probe_failed": t.get("public_probe_failed"),
                   "public_probe_ran": t.get("public_probe_ran"), "public_probe_reason": t.get("public_probe_reason"),
                   "exec_repairs": t.get("exec_repairs"), "probe_repairs": t.get("probe_repairs"),
                   "probe_repair_budget": t.get("probe_repair_budget"),
                   "correctness_asserted": t.get("correctness_asserted"),
                   "cases": cs, "work_files": nf,
                   "void": vn, "void_reason": rn,                       # ← R553 预注册口径
                   "void_old_r552_rule": vo, "void_old_reason": ro,      # ← R552 口径(并列, 禁替代)
                   "hygiene": {"rc": t.get("rc"), "stage": t.get("stage"), "upstream_rate": uc.get("rate"),
                               "upstream_unparseable": uc.get("unparseable"), "dumps_in_window": uc.get("dumps_in_window")},
                   "upstream": up}
            readings["windows"].setdefault("w%d" % w, {})[arm] = rec
            man["sources"][arm]["w%d" % w] = [{"file": tp.replace("/tmp/", ""), "bytes": os.path.getsize(tp),
                                              "sha256": sha(tp)}]
            if vn:
                readings["void"].append({"arm": arm, "win": "w%d" % w, "rc": t.get("rc"), "stage": t.get("stage"),
                                         "work_files": nf, "reason": rn, "old_rule_would_void": vo})
            elif write_snapshot:
                dst = os.path.join(HERE, "snapshots", "w%d" % w, "agent%s-%s" % (arm, TID), TID)
                if os.path.isdir(dst):
                    shutil.rmtree(dst)
                shutil.copytree(work, dst)
                man["sources"][arm]["w%d" % w].append({"snapshot": os.path.relpath(dst, REPO), "files": nfiles(dst)})
    return readings, man


def summarize(readings, arm_wins):
    out = {}
    for arm, wins in arm_wins.items():
        rows = [readings["windows"].get("w%d" % w, {}).get(arm) for w in wins]
        rows = [r for r in rows if r]
        val = [r for r in rows if not r["void"]]
        oldv = [r for r in rows if not r["void_old_r552_rule"]]
        q = [r["cases"]["pass"] for r in val if r["cases"] and r["cases"]["total"]]
        out[arm] = {
            "windows": ["w%d" % w for w in wins], "rows": len(rows), "n_valid": len(val),
            "valid_windows": ["w%d" % w for w, r in zip(wins, [readings["windows"].get("w%d" % w, {}).get(arm) for w in wins]) if r and not r["void"]],
            "n_valid_old_rule": len(oldv),
            "quality": ["%d/%d" % (r["cases"]["pass"], r["cases"]["total"]) for r in val if r["cases"] and r["cases"]["total"]],
            "median": sorted(q)[len(q) // 2] if q else None,
            "range": (max(q) - min(q)) if len(q) > 1 else (0 if q else None),
            "calls_sum": sum(r["calls"] or 0 for r in val),
            "prompt_sum": sum(r["prompt_tokens"] or 0 for r in val),
            "new_prompt_sum": sum((r["prompt_tokens"] or 0) - (r["cache_hit_tokens"] or 0) for r in val),
            "completion_sum": sum(r["completion_tokens"] or 0 for r in val),
        }
        # 逐窗并列(不挑选)
        out[arm]["per_window"] = [{"win": "w%d" % w,
                                   "cases": ("%d/%d" % (r["cases"]["pass"], r["cases"]["total"])) if r["cases"] and r["cases"]["total"] else "0/0",
                                   "void_new": r["void"], "void_old": r["void_old_r552_rule"],
                                   "rc": r["rc"], "calls": r["calls"]}
                                  for w, r in zip(wins, [readings["windows"].get("w%d" % w, {}).get(arm) for w in wins]) if r]
    return out


def main():
    sc = voidrule_selfcheck()
    print("[判据自检] has_teeth=%s delta=%s" % (sc["has_teeth"], sc["delta_cases"]))
    # --- R553 新窗 ---
    rd553, man553 = ingest(SRC_R553, "R553", True)
    ws = {a: w for a, _, w in SRC_R553}
    rd553["summary"] = summarize(rd553, ws)
    # 起手闸 C 混淆矩阵(hygiene 单列, 不作判据)
    cm = {"PASS": 0, "BLOCKED": 0, "details": []}
    for k, v in rd553["precheck"].items():
        vd = v.get("verdict") or ("ERROR rc=%s" % v.get("rc"))
        cm[vd] = cm.get(vd, 0) + 1
        cm["details"].append({"key": k, "verdict": vd, "task": v.get("verdict")})
    rd553["precheck_confusion"] = cm
    io.open(os.path.join(HERE, "readings-r553.json"), "w", encoding="utf-8").write(
        json.dumps(rd553, ensure_ascii=False, indent=1))
    io.open(os.path.join(HERE, "source-manifest.json"), "w", encoding="utf-8").write(
        json.dumps(man553, ensure_ascii=False, indent=1))
    # --- R552 追溯回算(只读, 不写 R552 任何文件) ---
    ret = {"round": "R552", "kind": "RETRO_RECOMPUTE", "read_only": True,
           "note": "用 R553 新口径重读 R552 已落盘的 24 窗; 与 R552 §2 已公布读数**并列**, 禁相减/禁替代。",
           "void_rule": rd553["void_rule"]}
    rdr, _ = ingest(SRC_R552, "R552", False)
    ws2 = {a: w for a, _, w in SRC_R552}
    ret["windows"] = rdr["windows"]
    ret["summary"] = summarize(rdr, ws2)
    ret["r552_published"] = {"rule": "R552 预注册口径(旧规则)", "valid_windows": {"b0": 0, "b1": 2, "b2": 2},
                             "quality_artifact": {"b0": "0/58×4,58/58,55/58", "b1": "0/58×3,45,47,47,53,56,58",
                                                  "b2": "0/58,45,53,54,58×4"}}
    io.open(os.path.join(HERE, "readings-r552-retro.json"), "w", encoding="utf-8").write(
        json.dumps(ret, ensure_ascii=False, indent=1))
    # --- evidence/windows + report.json (R553) ---
    ew = os.path.join(HERE, "evidence/windows")
    if os.path.isdir(ew):
        for d in sorted(os.listdir(ew)):
            ap = os.path.join(ew, d, "artifacts.json")
            try:
                if os.path.isfile(ap) and not (rd(ap).get("arms") or {}):
                    shutil.rmtree(os.path.join(ew, d))
            except Exception:
                pass
    for _, _, wins in SRC_R553:
        for w in wins:
            arms, rows = {}, []
            for a2, _, ws3 in SRC_R553:
                if w not in ws3:
                    continue
                rec = rd553["windows"].get("w%d" % w, {}).get(a2)
                if not rec or rec["void"]:
                    continue
                cs = rec["cases"]
                allp = bool(cs and cs["total"] and cs["pass"] == cs["total"])
                arms["%s-%s" % (a2, TID)] = {"snapshot": "snapshots/w%d/agent%s-%s/%s" % (w, a2, TID, TID),
                                             "all_pass": allp}
                rows.append({"arm": "%s-%s" % (a2, TID), "tid": TID, "side": "agent", "all_pass": allp,
                             "cases_pass": cs["pass"], "cases_total": cs["total"], "hidden_cases": 58,
                             "cases_rc": 0 if allp else 1, "claim_src": "cases.txt(R553 运行树自判)"})
            if not arms:
                continue     # 真 VOID 窗 ⇒ 不建窗目录(空窗目录会让前置器判『快照缺失』假红)
            wdir = os.path.join(ew, "w%d" % w)
            os.makedirs(wdir, exist_ok=True)
            io.open(os.path.join(wdir, "artifacts.json"), "w", encoding="utf-8").write(
                json.dumps({"window": "w%d" % w, "run_dir": "r1_%d (各臂同窗号)" % w, "arms": arms},
                           ensure_ascii=False, indent=1))
            io.open(os.path.join(wdir, "report.json"), "w", encoding="utf-8").write(
                json.dumps({"rows": rows, "note": "自报读数由运行树 cases.txt 派生; 独立重跑见前置器"},
                           ensure_ascii=False, indent=1))
    ts = rd(os.path.join(REPO, "eval/rover/r542/taskset-r542.json"))
    ts["round"] = "r553"
    ts["source"] = "eval/rover/r542/taskset-r542.json (g1 单题面, 逐字节同)"
    io.open(os.path.join(HERE, "taskset-r553.json"), "w", encoding="utf-8").write(
        json.dumps(ts, ensure_ascii=False, indent=1))
    # 题面夹具的**逐字节副本**必须落在轮目录下(前置器 rdir = 轮目录, 非快照目录; 缺 ⇒ missing_case_script 假红)。
    # 注意: 用例脚本以自身目录为基准读 cases-r521.json ⇒ 整个 cases/ 目录都要复制, 只复制脚本会 rc=1 cases=0/0。
    os.makedirs(os.path.join(HERE, "cases"), exist_ok=True)
    for _fn in sorted(os.listdir(os.path.join(REPO, "eval/rover/r552/cases"))):
        shutil.copy2(os.path.join(REPO, "eval/rover/r552/cases", _fn),
                     os.path.join(HERE, "cases", _fn))
    print("== R553 逐臂 (新口径 / 旧口径 并列) ==")
    for a, s in rd553["summary"].items():
        print("  %-7s 有效窗 %d/%d (旧口径 %d) 质量 %s 中位 %s 极差 %s 调用Σ %s 新算promptΣ %s completionΣ %s" % (
            a, s["n_valid"], s["rows"], s["n_valid_old_rule"], s["quality"], s["median"], s["range"],
            s["calls_sum"], s["new_prompt_sum"], s["completion_sum"]))
    print("== R552 追溯回算 (新口径) ==")
    for a, s in ret["summary"].items():
        print("  %-7s 有效窗 %d/%d (旧口径 %d) 质量 %s 中位 %s 极差 %s" % (
            a, s["n_valid"], s["rows"], s["n_valid_old_rule"], s["quality"], s["median"], s["range"]))
    print("[起手闸C] %s" % {k: v for k, v in cm.items() if k != "details"})


if __name__ == "__main__":
    main()
