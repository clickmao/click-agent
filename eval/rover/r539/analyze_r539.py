#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R539 分析器：role 轴 A/B（含实发 prompt 机检）+ 成本分列 + 外部真值列 + rc8 机检摘要。

口径（沿用 R502/R505/R532/R536，禁止跨轮相减）：
  - tokens 真值取中继 usage（adapter 落盘）；缺 usage ⇒ unreported，禁按 0 冒充。
  - calls 按 adapter 落盘文件数（一次请求一个文件；request_id 语义见 usage_from_dumps）。
  - R1 台账自带 calls/prompt/completion，仅作**对账**用，不顶替中继真值。
  - 同窗唯一变量 = role 挂载；主对照 = R1r vs A1-on（同窗同题同模型），外部参照 = C-codex。
  - 单窗=噪声：本器只出逐窗读数 + 极差，不给合并均值；跨轮禁相减。
"""
from __future__ import annotations
import argparse, importlib.util, json, os, sys

REPO = "/home/agentuser/AgentFramework"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


UFD = _load(os.path.join(REPO, "eval/rover/r539/usage_from_dumps.py"), "ufd539")


def usage(dump_dir, i0, i1, side="agent"):
    if not os.path.isdir(dump_dir) or i0 is None:
        return None
    return UFD.collect(dump_dir, side, i0, i1)


def msgs_of(blob):
    req = (blob.get("request") or {}).get("upstream_request") or {}
    msgs = req.get("messages") or []
    if not isinstance(msgs, list):
        return []
    return [m for m in msgs if isinstance(m, dict)]


def content_of(m):
    c = m.get("content")
    if isinstance(c, list):
        return "".join(x.get("text") or "" for x in c if isinstance(x, dict))
    return c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)


def dumps_in(dump_dir, i0, i1, side="agent"):
    if not os.path.isdir(dump_dir):
        return []
    out = []
    for fn in sorted(os.listdir(dump_dir)):
        if not fn.startswith("side-%s-" % side) or not fn.endswith(".json"):
            continue
        try:
            idx = int(fn.rsplit("-", 1)[1].split(".")[0])
        except Exception:
            continue
        if i0 is not None and (idx < i0 or idx > i1):
            continue
        try:
            out.append((idx, json.load(open(os.path.join(dump_dir, fn), encoding="utf-8"))))
        except Exception:
            continue
    return out


def role_mount_check(dump_dir, i0, i1, marker):
    """实发 prompt 机检：role 段必须出现在 user 轮，且不在首条(system/前缀)里。"""
    res = {"dumps_scanned": 0, "marker_in": [], "marker_in_prefix": False,
           "marker_in_user": False, "marker_in_system": False, "user_msgs_total": 0}
    for idx, blob in dumps_in(dump_dir, i0, i1):
        res["dumps_scanned"] += 1
        msgs = msgs_of(blob)
        for k, m in enumerate(msgs):
            txt = content_of(m)
            r = str(m.get("role") or "")
            if r == "user":
                res["user_msgs_total"] += 1
            if marker and marker in txt:
                res["marker_in"].append({"idx": idx, "pos": k, "role": r})
                if k == 0:
                    res["marker_in_prefix"] = True
                if r == "user":
                    res["marker_in_user"] = True
                if r in ("system", "developer"):
                    res["marker_in_system"] = True
    return res


def cases(path):
    if not os.path.isfile(path):
        return {"n_pass": 0, "n": 0, "rc": None, "verdict": None}
    lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    rc = None
    if lines and lines[-1].strip().lstrip("-").isdigit():
        rc = int(lines[-1].strip()); lines = lines[:-1]
    npass = sum(1 for l in lines if l.startswith("CASE ") and " PASS" in l)
    n = sum(1 for l in lines if l.startswith("CASE "))
    v = None
    for l in lines:
        if l.startswith("MS1_VERDICT "):
            v = l.split(" ", 1)[1]
    return {"n_pass": npass, "n": n, "rc": rc, "verdict": v}


def transcript(path):
    if not os.path.isfile(path):
        return {}
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round-dir", required=True)
    ap.add_argument("--windows", default="w1 w2 w3")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    R = a.round_dir
    wins = [w for w in __import__("re").split(r"[,\s]+", a.windows) if w]
    ts = json.load(open(os.path.join(R, "taskset-r539.json"), encoding="utf-8"))
    hid = {t["tid"]: int(t["hidden_cases"]) for t in ts["tasks"]}
    marker = "prefer_clarify_first"
    report = {"round": "r539", "windows": {}, "per_window_kpi": {}, "kpi_deltas_pct": [],
              "role_axis": {}, "codex": {}, "rc_table": {}, "ms1": {}, "notes": []}

    def idx_map(D):
        m = {}
        p = os.path.join(D, "logs/idx.txt")
        if os.path.isfile(p):
            for line in open(p, encoding="utf-8"):
                parts = line.split()
                if len(parts) == 3:
                    m[parts[0]] = (int(parts[1]), int(parts[2]))
        return m

    for W in wins:
        D = os.path.join(R, "run-%s" % W)
        dump = os.path.join(D, "adapter")
        im = idx_map(D)
        wd = {"arms": {}, "transcripts": {}}
        for tag, (i0, i1) in im.items():
            side = "codex" if tag.startswith("C-codex") else "agent"
            if side == "codex":
                i0, i1 = 1, 10 ** 9          # codex 侧独占 side-codex-* 命名 ⇒ 全窗计数（idx.txt 的 codex 区间不可靠）
            u = usage(dump, i0, i1, side)
            # 目录形态: <arm>/<tid>; tag = "<arm>-<tid>"
            arm = tag.rsplit("-", 1)[0]; tid = tag.rsplit("-", 1)[1]
            base = os.path.join(D, arm, tid)
            c = cases(os.path.join(base, "cases.txt"))
            tr = transcript(os.path.join(base, "transcript.json"))
            wd["arms"][tag] = {"side": side, "range": [i0, i1],
                               "calls": (u or {}).get("calls"), "prompt_tokens": (u or {}).get("prompt_tokens"),
                               "completion_tokens": (u or {}).get("completion_tokens"),
                               "total_tokens": (u or {}).get("total_tokens"),
                               "cached_tokens": (u or {}).get("cached_tokens"),
                               "unreported_usage": (u or {}).get("unreported_usage"),
                               "models": (u or {}).get("models"),
                               "cases_pass": c["n_pass"], "cases_total": c["n"], "cases_rc": c["rc"],
                               "hidden": hid.get(tid)}
            report["rc_table"].setdefault(tag, {})[W] = {"rc": tr.get("rc"), "cases": "%s/%s" % (c["n_pass"], c["n"])}
            if tr:
                wd["transcripts"][tag] = {k: tr.get(k) for k in
                                          ("rc", "stage", "steps_executed", "plan_steps_total", "self_test_unmet",
                                           "correctness_asserted", "role_note_chars", "prefix_chars", "prefix_sha256",
                                           "calls", "prompt_tokens", "completion_tokens", "tag")}

        # --- role 轴 A/B (J1) ---
        nr = wd["transcripts"].get("R1nr-t1", {})
        rr = wd["transcripts"].get("R1r-t1", {})
        j1a = nr.get("prefix_sha256") and (nr.get("prefix_sha256") == rr.get("prefix_sha256"))
        j1b = (int(rr.get("role_note_chars") or 0) > 0) and (int(nr.get("role_note_chars") or 0) == 0)
        rng = im.get("R1r-t1")
        j1c = role_mount_check(dump, rng[0], rng[1], marker) if rng else {}
        rngn = im.get("R1nr-t1")
        j1c_neg = role_mount_check(dump, rngn[0], rngn[1], marker) if rngn else {}
        wd["role_axis"] = {"prefix_sha_equal": bool(j1a), "role_note_chars_AB": [nr.get("role_note_chars"), rr.get("role_note_chars")],
                           "role_note_ok": bool(j1b), "role_in_user_turn": bool(j1c.get("marker_in_user")),
                           "role_in_prefix": bool(j1c.get("marker_in_prefix")), "role_in_system": bool(j1c.get("marker_in_system")),
                           "dumps_scanned": j1c.get("dumps_scanned"), "user_msgs_total": j1c.get("user_msgs_total"),
                           "negative_control_off_arm_marker_hits": len(j1c_neg.get("marker_in") or [])}
        report["role_axis"][W] = {k: v for k, v in wd["role_axis"].items() if k != "marker_hits"}

        # --- 主 KPI (J2): 同窗同题 R1r vs A1-on ---
        r1 = wd["arms"].get("R1r-t1", {}); a1 = wd["arms"].get("A1-on-t1", {})
        kpi = {}
        if r1.get("calls") and a1.get("calls"):
            kpi["calls"] = {"A1-on": a1["calls"], "R1r": r1["calls"], "delta_pct": round(100.0 * (1 - r1["calls"] / a1["calls"]), 1)}
        if r1.get("total_tokens") and a1.get("total_tokens"):
            kpi["tokens"] = {"A1-on": a1["total_tokens"], "R1r": r1["total_tokens"],
                             "delta_pct": round(100.0 * (1 - r1["total_tokens"] / a1["total_tokens"]), 1)}
        kpi["correctness"] = {"A1-on": "%s/%s" % (a1.get("cases_pass"), a1.get("hidden")),
                              "R1r": "%s/%s" % (r1.get("cases_pass"), r1.get("hidden"))}
        report["per_window_kpi"][W] = kpi
        if "tokens" in kpi:
            report["kpi_deltas_pct"].append(kpi["tokens"]["delta_pct"] if kpi["tokens"].get("delta_pct") is not None else None)
        # 外部真值列
        cx = wd["arms"].get("C-codex-t1", {})
        report["codex"][W] = {"calls": cx.get("calls"), "total_tokens": cx.get("total_tokens"),
                              "cases": "%s/%s" % (cx.get("cases_pass"), cx.get("hidden")), "ok": cx.get("cases_rc") == 0}
        m1 = wd["arms"].get("R1r-m1", {})
        report["windows"][W] = wd
        report.setdefault("m1_face", {})[W] = {"cases": "%s/%s" % (m1.get("cases_pass"), m1.get("hidden")), "rc": wd["transcripts"].get("R1r-m1", {}).get("rc")}
        # ms1 探针 (J3)
        if os.path.isfile(os.path.join(D, "R1ms/ms1/cases.txt")):
            cs = cases(os.path.join(D, "R1ms/ms1/cases.txt"))
            tr = transcript(os.path.join(D, "R1ms/ms1/transcript.json"))
            report["ms1"] = {"window": W, "cases": "%s/%s" % (cs["n_pass"], cs["n"]), "cases_rc": cs["rc"],
                             "verdict_text": cs["verdict"], "rc": tr.get("rc"), "steps_executed": tr.get("steps_executed"),
                             "plan_steps_total": tr.get("plan_steps_total"), "reason_head": str(tr.get("reason"))[:160],
                             "兑现": bool(cs["rc"] == 0 and cs["n_pass"] == cs["n"] and cs["n"] > 0)}

    ds = [d for d in report["kpi_deltas_pct"] if d is not None]
    report["kpi_delta_range"] = [min(ds), max(ds)] if ds else None
    report["notes"].append("单窗=噪声: 只报逐窗 + 极差; 跨轮禁相减。")
    report["notes"].append("外部真值列 ok=false ⇒ 该窗对照 unreliable。")

    out = a.out or os.path.join(R, "analyze-r539.json")
    json.dump(report, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("== R539 分析 (%s) ==" % out)
    for W in wins:
        wd = report["windows"].get(W, {})
        ra = report["role_axis"].get(W, {})
        print("-- %s  role轴: prefix_sha_equal=%s role_note_chars(A/B)=%s role_in_user=%s in_prefix=%s in_system=%s 反控命中=%s"
              % (W, ra.get("prefix_sha_equal"), ra.get("role_note_chars_AB"), ra.get("role_in_user_turn"),
                 ra.get("role_in_prefix"), ra.get("role_in_system"), ra.get("negative_control_off_arm_marker_hits")))
        for tag, v in sorted(wd.get("arms", {}).items()):
            print("   臂 %-11s calls=%-3s tok=%-7s cases=%s/%s rc=%s models=%s unreported=%s"
                  % (tag, v.get("calls"), v.get("total_tokens"), v.get("cases_pass"), v.get("hidden"),
                     v.get("cases_rc"), ",".join(v.get("models") or []), v.get("unreported_usage")))
        k = report["per_window_kpi"].get(W, {})
        print("   主KPI %s: calls %s | tokens %s | 正确性 %s"
              % (W, k.get("calls"), k.get("tokens"), k.get("correctness")))
        print("   外部列 codex: %s" % json.dumps(report["codex"].get(W), ensure_ascii=False))
    print("降幅极差(逐窗 token Δ%%) = %s" % (report["kpi_delta_range"],))
    print("m1 跨族面 = %s" % json.dumps(report.get("m1_face"), ensure_ascii=False))
    print("ms1 探针 = %s" % json.dumps(report.get("ms1"), ensure_ascii=False))
    rc8 = [(t, W, v.get("rc")) for t in report["rc_table"] for W, v in report["rc_table"][t].items() if v.get("rc") == 8]
    print("rc=8 计数 = %d %s" % (len(rc8), rc8[:6]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
