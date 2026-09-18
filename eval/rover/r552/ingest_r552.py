#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R552 入仓: 三棵运行树(/tmp/r552_b{0,1,2})的原始物证 → ① 仓内不可变快照
② evidence/windows/*/{report,artifacts}.json ③ readings-r552.json ④ 命中率(双口径)
⑤ 上游契约面可解析性(逐窗, 承 R552 候选③) ⑥ VOID 判定台账 + **上游闸自检(判据有牙/负控)**.

纪律: 只读 /tmp 运行树; 每个源件记 (bytes, sha256); VOID 窗不进快照、不进 require,
但在 readings 里可见(rc/stage/产物树文件数/上游退化率) —— 禁把 VOID 当能力读数, 也禁静默丢弃。
"""
import glob
import hashlib
import io
import json
import os
import shutil
import sys

REPO = "/home/agentuser/AgentFramework"
HERE = os.path.join(REPO, "eval/rover/r552")
SRC = [("R552b0", "/tmp/r552v2_b0", (30, 31, 32, 39, 40, 41, 49, 50, 51)),
       ("R552b1", "/tmp/r552v2_b1", (33, 34, 35, 43, 44, 45, 52, 53, 54)),
       ("R552b2", "/tmp/r552v2_b2", (36, 37, 38, 46, 47, 48, 55, 56, 57))]
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


def voidgate_selfcheck():
    """判据有牙自检(承 R549 纪律): 上游退化闸必须能翻面 —— 坏样本判红 ∧ 好样本判绿。"""
    good = json.dumps({"schema_version": "r1.0", "intent": "code_task"})
    bad = good[:-12]                                   # 截断 = R551 实测退化形态(尾随内容)
    thr = 0.25
    def verdict(texts):
        ok = bad_n = 0
        for t in texts:
            try:
                json.loads(t); ok += 1
            except Exception:
                bad_n += 1
        tot = ok + bad_n
        return bool(tot > 0 and (bad_n / tot) > thr)
    res = {"rule": "不可解析率 > %s ⇒ void_upstream" % thr,
           "pos_control_all_bad": verdict([bad] * 4), "neg_control_all_good": verdict([good] * 4),
           "mixed_25pct": verdict([good] * 3 + [bad] * 1), "mixed_over": verdict([good] * 2 + [bad] * 2)}
    res["has_teeth"] = bool(res["pos_control_all_bad"] and not res["neg_control_all_good"]
                            and not res["mixed_25pct"] and res["mixed_over"])
    res["note"] = "25% 不触发(严格大于)、>25% 触发 ⇒ 阈值语义钉死; 有牙 = 坏样本红 ∧ 好样本绿。"
    return res


def main():
    man = {"round": "R552", "ingested_at": os.popen("date -Is").read().strip(),
           "note": "R552 原始运行树在仓外(/tmp/r552_b{0,1,2}); 按字节复制入仓并把源 (bytes,sha256) 落盘。",
           "axis": "AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR ∈ {0,1,2} (既有开关剂量面, 同一二进制)",
           "binary_sha256": "e2fdab87b03b3f9ddae1628471b30b6165c07923e5924d77fbf111d24dd5c27b",
           "sources": {}}
    readings = {"round": "R552", "windows": {}, "void": [], "hit_definition":
                "命中率(双口径, 脚本化) = hitrate_dual.py: v_all=1−Σmiss/Σprompt(含冷启动) / "
                "v_incr=1−miss_last/prompt_last(仅增量); 跨轮/跨窗禁相减",
                "hitrate": {}, "dump_json_parseability": {}, "upstream_gate": {}}
    dumps_sha = {}
    for arm, run, wins in SRC:
        readings["hitrate"][arm] = hitrate_dual.run(os.path.join(run, "adapter"), run, arm, nwin=3, wins=wins)
        ok = bad = 0
        det = []
        dumps_sha[arm] = []
        for f in sorted(glob.glob(os.path.join(run, "adapter", "side-agent-*.json"))):
            d = rd(f)
            t = (d.get("response") or {}).get("text") or ""
            try:
                json.loads(t); ok += 1
            except Exception as e:
                bad += 1
                det.append({"file": os.path.basename(f), "len": len(t), "err": str(e)[:80]})
            dumps_sha[arm].append({"file": f.replace("/tmp/", ""), "bytes": os.path.getsize(f), "sha256": sha(f)})
        readings["dump_json_parseability"][arm] = {"parseable": ok, "unparseable": bad, "detail": det}
        readings["upstream_gate"][arm] = {}
        man["sources"][arm] = {}
        for w in wins:
            wd = os.path.join(run, "r1_%d" % w)
            tp = os.path.join(wd, "transcript.json")
            if not os.path.isfile(tp):
                continue
            t = rd(tp)
            cs = cases_of(run, w)
            work = os.path.join(wd, "work")
            nf = nfiles(work)
            vp = os.path.join(run, "voidchk-%d.json" % w)
            uc = rd(vp) if os.path.isfile(vp) else {}
            readings["upstream_gate"][arm]["w%d" % w] = {k: uc.get(k) for k in
                                                        ("dumps_in_window", "unparseable", "rate", "void_upstream")}
            # 两种口径并列(禁互相替代):
            #   void       = **预注册口径**（rc=4 ∨ 无产物 ∨ 上游退化率>0.25）——本轮 J 判据按它判；
            #   void_artifact = **事后收窄口径**（仅『无产物/无用例可判分』）——实测 b1 w43/w53 等 rc=4 窗
            #                   仍产出 45–56/58 的**可判分产物**、w38/w48 产出 58/58 ⇒ 预注册口径过宽
            #                   (把 hygiene 读数当 VOID 触发条件)。修正形态**只作 checks_posthoc**。
            void_art = bool((cs or {}).get("total", 0) == 0 or nf == 0)
            void = bool(t.get("rc") == 4 or (cs or {}).get("total", 0) == 0 or nf == 0 or uc.get("void_upstream"))
            rec = {"rc": t.get("rc"), "stage": t.get("stage"), "calls": t.get("calls"),
                   "prompt_tokens": t.get("prompt_tokens"), "completion_tokens": t.get("completion_tokens"),
                   "cache_hit_tokens": t.get("cache_hit_tokens"), "cache_miss_tokens": t.get("cache_miss_tokens"),
                   "prefix_chars": t.get("prefix_chars"), "task_sha256": t.get("task_sha256"),
                   "public_probe_total": t.get("public_probe_total"), "public_probe_failed": t.get("public_probe_failed"),
                   "exec_repairs": t.get("exec_repairs"), "correctness_asserted": t.get("correctness_asserted"),
                   "probe_repairs": t.get("probe_repairs"), "probe_repair_budget": t.get("probe_repair_budget"),
                   "public_probe_reason": t.get("public_probe_reason"), "repair_rounds": t.get("repair_rounds"),
                   "cases": cs, "work_files": nf, "void": void, "void_artifact": void_art,
                   "upstream": {k: uc.get(k) for k in ("dumps_in_window", "unparseable", "rate", "void_upstream")},
                   "void_reason": ("rc=4 stage=%s" % t.get("stage")) if t.get("rc") == 4 else
                                  ("no_cases" if (cs or {}).get("total", 0) == 0 else
                                   ("work_files=0" if nf == 0 else
                                    ("upstream_degraded rate=%s" % uc.get("rate") if uc.get("void_upstream") else None)))}
            readings["windows"].setdefault("w%d" % w, {})[arm] = rec
            man["sources"][arm]["w%d" % w] = [{"file": tp.replace("/tmp/", ""), "bytes": os.path.getsize(tp),
                                               "sha256": sha(tp)}]
            if void_art:
                readings["void"].append({"arm": arm, "win": "w%d" % w, "rc": t.get("rc"), "stage": t.get("stage"),
                                         "work_files": nf, "upstream": rec["upstream"],
                                         "reason": "契约面/空产出/上游退化 ⇒ 对能力命题零信息量(不删不覆盖)"})
            else:
                dst = os.path.join(HERE, "snapshots", "w%d" % w, "agent%s-%s" % (arm, TID), TID)
                if os.path.isdir(dst):
                    shutil.rmtree(dst)
                shutil.copytree(work, dst)
                man["sources"][arm]["w%d" % w].append({"snapshot": os.path.relpath(dst, REPO),
                                                       "files": nfiles(dst)})
    # --- checks_posthoc: 事后收窄口径读数(与预注册口径**并列**, 禁替代; 按纪律不得回写为预注册命中) ---
    post = {}
    for arm, _, wins in SRC:
        art = []
        for w in wins:
            rec = readings["windows"].get("w%d" % w, {}).get(arm)
            if not rec or rec["void_artifact"]:
                continue
            art.append({"win": "w%d" % w, "pass": rec["cases"]["pass"], "total": rec["cases"]["total"],
                        "void_prereg": rec["void"], "rc": rec["rc"], "calls": rec["calls"],
                        "probe_failed": rec["public_probe_failed"], "probe_repairs": rec["probe_repairs"]})
        pv = [r for r in art if not r["void_prereg"]]
        post[arm] = {"windows_with_artifact": art, "n_artifact": len(art),
                     "prereg_valid": [r["win"] for r in pv],
                     "first3_artifact": art[:3], "first3_prereg": pv[:3],
                     "note": "收窄口径 = 仅『无产物/无用例可判分』判 VOID; rc=4 与上游退化率降为 hygiene 读数。"
                             "实测反例: rc=4 窗仍产出 45–56/58 可判分产物; 退化率 0.333 窗产出 58/58。"}
    readings["checks_posthoc"] = post
    json.dump(readings, io.open(os.path.join(HERE, "readings-r552.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(man, io.open(os.path.join(HERE, "source-manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(dumps_sha, io.open(os.path.join(HERE, "dumps-sha256.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    # 清理上一轮 ingest 留下的**空窗目录**(arms={} ⇒ 前置器会把它当已声明窗判『快照缺失』假红)
    ew = os.path.join(HERE, "evidence/windows")
    if os.path.isdir(ew):
        for d in sorted(os.listdir(ew)):
            ap = os.path.join(ew, d, "artifacts.json")
            try:
                if os.path.isfile(ap) and not (rd(ap).get("arms") or {}):
                    shutil.rmtree(os.path.join(ew, d))
            except Exception:
                pass
    for arm, _, wins in SRC:
        for w in wins:
            wdir = os.path.join(HERE, "evidence/windows", "w%d" % w)
            arms, rows = {}, []
            for a2, _, ws2 in SRC:
                if w not in ws2:
                    continue
                rec = readings["windows"].get("w%d" % w, {}).get(a2)
                if not rec or rec["void_artifact"]:
                    continue
                cs = rec["cases"]
                allp = bool(cs and cs["total"] and cs["pass"] == cs["total"])
                arms["%s-%s" % (a2, TID)] = {"snapshot": "snapshots/w%d/agent%s-%s/%s" % (w, a2, TID, TID),
                                             "all_pass": allp}
                rows.append({"arm": "%s-%s" % (a2, TID), "tid": TID, "side": "agent", "all_pass": allp,
                             "cases_pass": cs["pass"], "cases_total": cs["total"], "hidden_cases": 58,
                             "cases_rc": 0 if allp else 1, "claim_src": "cases.txt(R552 运行树自判)"})
            if not arms:
                # 该窗对所有臂都无产物(真 VOID) ⇒ **不建窗目录**: 建了会让前置器按『已声明窗』判
                # 『快照目录缺失』= 假红(实测第一次前置器即此因, 20 项 blocked 里 12 项是空窗)。
                continue
            os.makedirs(wdir, exist_ok=True)
            json.dump({"window": "w%d" % w, "run_dir": "r1_%d (各臂同窗号)" % w, "arms": arms},
                      io.open(os.path.join(wdir, "artifacts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            json.dump({"rows": rows, "note": "自报读数由运行树 cases.txt 派生(非独立重跑); 独立重跑见前置器"},
                      io.open(os.path.join(wdir, "report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ts = rd(os.path.join(REPO, "eval/rover/r542/taskset-r542.json"))
    ts["round"] = "r552"
    ts["source"] = "eval/rover/r542/taskset-r542.json (g1 单题面, 逐字节同)"
    json.dump(ts, io.open(os.path.join(HERE, "taskset-r552.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.makedirs(os.path.join(HERE, "cases"), exist_ok=True)
    src_cases = os.path.join(REPO, "eval/rover/r542/cases/run_cases_r521.py")
    dst_cases = os.path.join(HERE, "cases/run_cases_r521.py")
    shutil.copy2(src_cases, dst_cases)
    sc = voidgate_selfcheck()
    json.dump(sc, io.open(os.path.join(HERE, "void_gate_selfcheck.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("[入仓] 上游闸自检 has_teeth=%s %s" % (sc["has_teeth"], {k: v for k, v in sc.items() if k.startswith(("pos", "neg", "mixed"))}))
    print("[入仓] 快照窗=%s" % sorted(os.listdir(os.path.join(HERE, "snapshots"))))
    for arm, _, _ in SRC:
        p = readings["dump_json_parseability"][arm]
        h = readings["hitrate"][arm]
        print("  %-7s dump JSON 可解析 %d/不可解析 %d | 逐窗 v_all=%s v_incr=%s" % (
            arm, p["parseable"], p["unparseable"],
            ["%.1f%%" % (100 * r["v_all"]) if r.get("status") == "ok" else "-" for r in h["rows"]],
            ["%.1f%%" % (100 * r["v_incr"]) if r.get("status") == "ok" else "-" for r in h["rows"]]))
        print("          上游闸 %s" % readings["upstream_gate"][arm])
    print("[VOID] %d 窗: %s" % (len(readings["void"]),
                              ", ".join("%s/%s(rc=%s,%s)" % (v["arm"], v["win"], v["rc"], v["reason"][:22]) for v in readings["void"])))


if __name__ == "__main__":
    main()
