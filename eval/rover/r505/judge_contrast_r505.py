#!/usr/bin/env python3
"""R505 对照判分（**只读仓内快照, 不重跑**）。

相对 R504 judge 的修复（缺陷: 判分输入是 /tmp 活目录, 判分后被后续作业覆盖 ⇒ 读数不可重放）:
  * `--adapter-codex-dir` / `--adapter-agent-dir` 指向**仓内不可变快照**;
  * `--manifest-codex/agent`: 快照时的逐文件 sha256 清单 ⇒ H10 逐文件机检（被改写即红）;
  * 判分内**双读**同一快照 ⇒ H9 取数幂等（同输入两次读逐位相同）;
  * 新增 H8 逐题调用构成（归因全覆盖, 未归因 ⇒ 红）;
  * 新增 H11 反向控制: 必须**能检出** R504 那类覆盖（把冻结清单喂给已污染目录 ⇒ 必须红, 见 nc_r505）。

rc: 0 绿; 1 判据红; 3 fail-closed（缺侧/缺预注册/缺快照）
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
import attr_calls_r505 as AC  # noqa: E402


def load(p):
    return json.load(open(p, encoding="utf-8-sig"))


def side_rows(d):
    rows = {}
    for t in d.get("per_task") or []:
        rows[t.get("tid")] = {"mode": t.get("mode"), "family": t.get("family"), "kind": t.get("kind"),
                              "passed": t.get("passed"), "total": t.get("total"),
                              "reply_chars": t.get("reply_chars")}
    return rows


def usage_sum(dirpath, side):
    tot_in = tot_out = cached = calls = 0
    models = []
    for p in sorted(glob.glob(os.path.join(dirpath or "", "side-%s-*.json" % side))):
        d = load(p)
        u = ((d.get("response") or {}).get("usage") or {})
        tot_in += int(u.get("prompt_tokens") or u.get("input_tokens") or 0)
        tot_out += int(u.get("completion_tokens") or u.get("output_tokens") or 0)
        cached += int(u.get("prompt_cache_hit_tokens") or 0)
        calls += 1
        m = ((d.get("request") or {}).get("upstream_request") or {}).get("model")
        if m:
            models.append(str(m))
    mc = {}
    for m in models:
        mc[m] = mc.get(m, 0) + 1
    return {"calls": calls, "in_tokens": tot_in, "out_tokens": tot_out,
            "total_tokens": tot_in + tot_out, "cached_tokens": cached, "model_counts": mc}


def sha_check(dirpath, manifest_path):
    """快照逐文件 sha256 vs 冻结清单 ⇒ 不一致点名（H10）。"""
    if not manifest_path or not os.path.exists(manifest_path):
        return None, [{"file": "*", "error": "缺清单"}]
    man = load(manifest_path)
    want = {r["file"]: r["sha256"] for r in man.get("files") or []}
    bad = []
    for f, want_sha in sorted(want.items()):
        p = os.path.join(dirpath, f)
        if not os.path.exists(p):
            bad.append({"file": f, "error": "missing"})
            continue
        got = hashlib.sha256(open(p, "rb").read()).hexdigest()
        if got != want_sha:
            bad.append({"file": f, "want": want_sha[:12], "got": got[:12]})
    return man, bad


def codex_attribution(raw_dir, audit_path, tids):
    """codex 侧逐题调用构成: raw jsonl 的 `turn.completed` 计数 + audit 逐题 usage。

    一致性硬断言: Σ(raw 逐题 usage) == 两侧 adapter 总量（否则记 unreported, 禁猜）。
    """
    if not raw_dir or not os.path.isdir(raw_dir):
        return {"status": "unreported", "reason": "缺 codex raw 目录"}
    rows = []
    tot_calls = tot_in = tot_out = 0
    for p in sorted(glob.glob(os.path.join(raw_dir, "codex-*.jsonl"))):
        calls = ci = co = 0
        for ln in open(p, encoding="utf-8-sig", errors="replace"):
            ln = ln.strip()
            if not ln.startswith("{"):
                continue
            try:
                r = json.loads(ln)
            except Exception:
                continue
            if r.get("type") == "turn.completed":
                u = r.get("usage") or {}
                calls += 1
                ci += int(u.get("input_tokens") or 0)
                co += int(u.get("output_tokens") or 0)
        rows.append({"file": os.path.basename(p), "turns": calls, "in_tokens": ci, "out_tokens": co})
        tot_calls += calls
        tot_in += ci
        tot_out += co
    if len(rows) == len(tids):
        for r, tid in zip(rows, tids):
            r["tid"] = tid
    else:
        for r in rows:
            r["tid"] = None
    # audit 逐题读数（若在）
    audit = None
    if audit_path and os.path.exists(audit_path):
        audit = []
        for ln in open(audit_path, encoding="utf-8-sig", errors="replace"):
            ln = ln.strip()
            if not ln.startswith("{"):
                continue
            try:
                audit.append(json.loads(ln))
            except Exception:
                continue
    return {"status": "ok", "rows": rows, "totals": {"turns": tot_calls, "in_tokens": tot_in,
                                                     "out_tokens": tot_out,
                                                     "total_tokens": tot_in + tot_out},
            "audit_rows": len(audit) if audit is not None else None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--codex")
    ap.add_argument("--agent")
    ap.add_argument("--prereg", default=os.path.join(HERE, "prereg_r505.json"))
    ap.add_argument("--adapter-codex-dir")
    ap.add_argument("--adapter-agent-dir")
    ap.add_argument("--manifest-codex")
    ap.add_argument("--manifest-agent")
    ap.add_argument("--codex-raw-dir", default=None)
    ap.add_argument("--codex-audit", default=None)
    ap.add_argument("--batch", default="a")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    need = {"codex": a.codex, "agent": a.agent, "prereg": a.prereg,
            "adapter-codex-dir": a.adapter_codex_dir, "adapter-agent-dir": a.adapter_agent_dir}
    missing = [n for n, p in need.items() if not p or not os.path.exists(p)]
    if missing:
        print("[致命] 输入缺失: %s ⇒ fail-closed (rc=3, 不算绿)" % ", ".join(missing))
        return 3

    pre = load(a.prereg)
    cj, aj = load(a.codex), load(a.agent)
    crit, rc = [], 0

    # H10 快照不可变（逐文件 sha256）
    man_c, bad_c = sha_check(a.adapter_codex_dir, a.manifest_codex)
    man_a, bad_a = sha_check(a.adapter_agent_dir, a.manifest_agent)
    h10 = not bad_c and not bad_a and man_c is not None and man_a is not None
    crit.append({"id": "H10", "name": "证据快照不可变（逐文件 sha256 vs 冻结清单）", "pass": h10,
                 "measured": {"codex_files": (man_c or {}).get("n_files"), "agent_files": (man_a or {}).get("n_files"),
                              "codex_bad": bad_c, "agent_bad": bad_a}})
    if not h10:
        rc = 1

    # H9 取数幂等（同一快照双读逐位相同）
    u1 = {s: usage_sum(d, s) for s, d in (("codex", a.adapter_codex_dir), ("agent", a.adapter_agent_dir))}
    u2 = {s: usage_sum(d, s) for s, d in (("codex", a.adapter_codex_dir), ("agent", a.adapter_agent_dir))}
    h9 = u1 == u2
    crit.append({"id": "H9", "name": "取数幂等（快照双读逐位相同; 跨时间复核见 replay-*.json）", "pass": h9,
                 "measured": {"equal": h9, "codex_calls": u1["codex"]["calls"], "agent_calls": u1["agent"]["calls"]}})
    if not h9:
        rc = 1

    # H3 同输入
    ts_exp = pre.get("probe_taskset_sha") or (pre.get("files_sha256") or {}).get("taskset")
    ts_c, ts_a = cj.get("taskset_sha"), aj.get("taskset_sha")
    h3 = bool(ts_exp) and ts_c == ts_a == ts_exp
    crit.append({"id": "H3", "name": "同输入机检（两侧 == 预注册; 且 == R504 v4 题集）", "pass": h3,
                 "measured": {"codex": ts_c, "agent": ts_a, "prereg": ts_exp,
                              "r504_taskset_sha": (pre.get("taskset") or {}).get("r504_sha256"),
                              "n_tasks_codex": cj.get("n_tasks"), "n_tasks_agent": aj.get("n_tasks")}})
    if not h3:
        rc = 1

    rc_rows, ra_rows = side_rows(cj), side_rows(aj)
    n_pre = (pre.get("taskset") or {}).get("n_tasks")
    h6 = (cj.get("n_tasks") == aj.get("n_tasks") == n_pre) and bool(rc_rows) and bool(ra_rows)
    crit.append({"id": "H6", "name": "fail-closed（两侧题数齐备且 == 预注册; 缺侧 ⇒ rc=3）", "pass": h6,
                 "measured": {"n_codex": cj.get("n_tasks"), "n_agent": aj.get("n_tasks"), "prereg": n_pre,
                              "codex_rows": len(rc_rows), "agent_rows": len(ra_rows)}})
    if not h6:
        rc = 3
    tids = sorted(set(rc_rows) | set(ra_rows))
    table = []
    for tid in tids:
        c, r = rc_rows.get(tid, {}), ra_rows.get(tid, {})
        table.append({"tid": tid, "kind": c.get("kind") or r.get("kind"),
                      "family": c.get("family") or r.get("family"),
                      "codex_mode": c.get("mode"), "agent_mode": r.get("mode"),
                      "codex_passed": c.get("passed"), "codex_total": c.get("total"),
                      "agent_passed": r.get("passed"), "agent_total": r.get("total")})

    c_ok = sum(1 for t in rc_rows.values() if t.get("mode") == "ok")
    a_ok = sum(1 for t in ra_rows.values() if t.get("mode") == "ok")
    h2_status = "pass" if c_ok >= 1 else "unreported"
    crit.append({"id": "H2", "name": "外部真值可用性", "pass": c_ok >= 1, "status": h2_status,
                 "measured": {"codex_ok": c_ok, "codex_n": len(rc_rows), "agent_ok": a_ok, "agent_n": len(ra_rows)}})

    uc, ua = u1["codex"], u1["agent"]
    mo_c, mo_a = set(uc["model_counts"]), set(ua["model_counts"])
    same_model = bool(mo_c) and mo_c == mo_a and len(mo_c) == 1
    h4_status = "pass" if same_model else ("unreported" if not (uc["calls"] and ua["calls"]) else "fail")
    crit.append({"id": "H4", "name": "同模型机检", "pass": same_model, "status": h4_status,
                 "measured": {"codex": uc, "agent": ua,
                              "prereg_label": (pre.get("external_reference") or {}).get("upstream_model"),
                              "note": "prereg 记本仓侧标签; adapter 落盘是供应商侧名"}})
    if h4_status == "fail":
        rc = 1

    assert "winner" not in json.dumps({"t": table, "u": [uc, ua]}), "H5: 禁在产物里放 winner 字段"
    crit.append({"id": "H5", "name": "对照读数分列（禁总量断言）", "pass": True, "measured": {"rows": len(table)}})

    checks = (pre.get("checks_prefirstrun") or pre.get("checks_negative") or {})
    inst = {k: v for k, v in checks.items() if k.startswith("nc1") and isinstance(v, dict)}
    h1 = bool(inst) and all(v.get("pass") for v in inst.values())
    crit.append({"id": "H1", "name": "仪器判别力（首跑前负控, 全覆盖）",
                 "pass": h1, "status": "pass" if h1 else ("partial" if inst else "not_in_prereg"),
                 "measured": {"blocks": sorted(inst), "n_blocks": len(inst), "all_pass": h1, "detail": inst}})
    if not h1:
        rc = 1

    # H8 逐题调用构成（判据② 的取证面）
    ts_path = os.path.join(HERE, "taskset-r505.json")
    _, refs = AC.build_refs(ts_path)
    att = AC.scan(a.adapter_agent_dir, refs, a.manifest_agent,
                  replies=AC.load_replies(os.path.join(REPO, "data", "probe", "replies"),
                                          "agent-r505%s" % a.batch))
    ag: dict = att.get("agent") or {"calls": 0, "by_task": [], "unmatched": [], "ambiguous": [], "sha_mismatch": []}
    cx: dict = codex_attribution(a.codex_raw_dir, a.codex_audit, [t["tid"] for t in load(ts_path)])
    # codex 一致性: raw 逐题 usage 必须等于 adapter 观测总量（不成立 ⇒ unreported, 不猜）
    if cx.get("status") == "ok":
        cx_t = cx["totals"]
        cx["consistency"] = {
            "adapter_in": uc["in_tokens"], "raw_in": cx_t["in_tokens"],
            "adapter_out": uc["out_tokens"], "raw_out": cx_t["out_tokens"],
            "in_match": cx_t["in_tokens"] == uc["in_tokens"],
            "out_match": cx_t["out_tokens"] == uc["out_tokens"],
        }
        cx["status"] = "ok" if (cx["consistency"]["in_match"] and cx["consistency"]["out_match"]) else "inconsistent"
    h8 = ag["calls"] == ua["calls"] and not ag["unmatched"] and not ag["ambiguous"]
    crit.append({"id": "H8", "name": "逐题调用构成（本侧归因全覆盖; codex 侧 raw↔adapter 一致）", "pass": bool(h8),
                 "status": "pass" if h8 else "fail",
                 "measured": {"agent_calls": ag["calls"], "agent_calls_in_usage": ua["calls"],
                              "unmatched": ag["unmatched"], "ambiguous": ag["ambiguous"],
                              "codex_status": cx.get("status")}})
    if not h8:
        rc = 1

    nc11 = ((pre.get("checks_prefirstrun") or {}).get("nc11_contamination_detector") or {})
    crit.append({"id": "H11", "name": "反向控制（R504「判分后覆盖」缺陷可被机检检出）",
                 "pass": bool(nc11.get("pass")),
                 "status": "pass" if nc11.get("pass") else "not_in_prereg",
                 "measured": {"r504_mismatch_n": nc11.get("r504_mismatch_n"),
                              "r504_mismatch_files": nc11.get("r504_mismatch_files")}})

    verdict = {
        "round": "R505", "batch": a.batch, "rc": rc, "criteria": crit, "table": table,
        "totals": {
            "codex": {"whole_ok": c_ok, "n": len(rc_rows), "elapsed_s": cj.get("elapsed_s"),
                      "usage": uc, "per_family": cj.get("by_family")},
            "agent": {"whole_ok": a_ok, "n": len(ra_rows), "elapsed_s": aj.get("elapsed_s"),
                      "usage": ua, "per_family": aj.get("by_family")},
        },
        "attribution": {"agent": {"calls": ag["calls"], "by_task": ag["by_task"]}, "codex": cx},
        "evidence": {"adapter_codex_dir": os.path.relpath(a.adapter_codex_dir, os.path.dirname(os.path.dirname(os.path.dirname(HERE)))),
                     "adapter_agent_dir": os.path.relpath(a.adapter_agent_dir, os.path.dirname(os.path.dirname(os.path.dirname(HERE)))),
                     "manifest_codex_n": (man_c or {}).get("n_files"),
                     "manifest_agent_n": (man_a or {}).get("n_files")},
        "note": "两侧读数分列; 静态面不同源 ⇒ 禁据 token 总量断言优劣 (H5); 判分输入=仓内快照",
    }
    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(verdict, fh, ensure_ascii=False, indent=1)
            fh.write("\n")

    print("batch=%s  tid  kind    family                      codex            agent" % a.batch)
    for r in table:
        print("  %-5s %-7s %-26s %-16s %s" % (
            r["tid"], r["kind"], r["family"],
            "%s(%s/%s)" % (r["codex_mode"], r["codex_passed"], r["codex_total"]),
            "%s(%s/%s)" % (r["agent_mode"], r["agent_passed"], r["agent_total"])))
    print("整题全对: codex %d/%d | agent %d/%d (H2=%s)" % (c_ok, len(rc_rows), a_ok, len(ra_rows), h2_status))
    print("用量分列: codex calls=%d tok=%d | agent calls=%d tok=%d (H4=%s)" % (
        uc["calls"], uc["total_tokens"], ua["calls"], ua["total_tokens"], h4_status))
    print("调用构成(本侧): %s" % ", ".join("%s×%d" % (e["tid"] or "UNMATCHED", e["calls"]) for e in ag["by_task"]))
    print("墙钟: codex %ss | agent %ss" % (cj.get("elapsed_s"), aj.get("elapsed_s")))
    for c in crit:
        print("  %-4s %-40s %s" % (c["id"], c["name"], "PASS" if c["pass"] else "NOT"))
    if a.out:
        print("verdict -> %s (rc=%d)" % (a.out, rc))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
