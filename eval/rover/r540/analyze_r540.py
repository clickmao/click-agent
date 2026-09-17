#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R540 读数器.

① 实发 prompt 机检 (role 段必须出现在发往上游的 user 轮, 且不在前缀) —— 修复 R539 缺陷:
   R539 的 msgs_of() 只读 side-*.json 的 request.upstream_request.messages, 而 agent 侧
   adapter 的 side dump 把 upstream_request 落成**摘要** (n_messages / prompt_sha8 /
   tail_messages[].head 截断) ⇒ msgs_of 恒空 ⇒ 三窗三检全 False(恒假阴性, 与"没挂上"不可分)。
   修法: 优先读 full-<side>-*.json (ADAPTER_DUMP_FULL=1 落盘的**裸 list[dict] 消息数组**),
   side 摘要作回退并显式标 partial=True(截断 ⇒ 阴性不可判)。
② 成本分列: 按 logs/idx.txt 的臂区间取 side-* 汇总 (calls / prompt / cached / completion / total)。
③ 降幅 vs A1-on (同窗同题), 逐窗报, 不合并。
用法: python3 analyze_r540.py --run-dir <D> --window w1 [--self-test]
"""
from __future__ import annotations
import argparse, io, json, os, re, sys

FNAME = re.compile(r"^side-([a-z0-9_]+)-(\d+)\.json$")
RFULL = re.compile(r"^full-([a-z0-9_]+)-(\d+)\.json$")
MARKER = "prefer_clarify_first"


# ---------- 形态自适应读数 (R540 修复点) -------------------------------------
def msgs_of(blob):
    """返回 (messages, partial)。支持两种落盘形态:
    A) 裸 list[dict] (full-*.json)                          ⇒ partial=False
    B) side-*.json 摘要 (upstream_request.messages 或 tail_messages[].head) ⇒ partial=True
    C) dict 里 messages 直挂 (兼容其它 adapter)             ⇒ partial=False
    """
    if isinstance(blob, list):
        return [m for m in blob if isinstance(m, dict)], False
    if isinstance(blob, dict):
        req = (blob.get("request") or blob).get("upstream_request") or blob.get("request") or {}
        msgs = req.get("messages") if isinstance(req, dict) else None
        if isinstance(msgs, list) and msgs:
            return [m for m in msgs if isinstance(m, dict)], False
        tail = req.get("tail_messages") if isinstance(req, dict) else None
        if isinstance(tail, list) and tail:
            out = []
            for m in tail:
                if not isinstance(m, dict):
                    continue
                mm = dict(m)
                if "head" in mm and "content" not in mm:
                    mm["content"] = mm.get("head") or ""
                out.append(mm)
            return out, True
        t = blob.get("messages")
        if isinstance(t, list):
            return [m for m in t if isinstance(m, dict)], False
    return [], False


def content_of(m):
    c = m.get("content")
    if isinstance(c, list):
        return " ".join(str((x or {}).get("text") or "") for x in c if isinstance(x, dict))
    return "" if c is None else str(c)


def read_dump(d, fn):
    try:
        return json.load(io.open(os.path.join(d, fn), encoding="utf-8"))
    except Exception:
        return None


def first_user_idx(msgs):
    for k, m in enumerate(msgs):
        if str(m.get("role")) == "user":
            return k
    return -1


def role_mount_check(d, side, i0, i1):
    """实发 prompt 机检: 优先 full-* (裸数组), 回退 side-* 摘要。"""
    res = {"side": side, "range": [i0, i1], "dumps_scanned": 0, "shape": None,
           "marker_in_user": False, "marker_in_prefix": False, "marker_in_system": False,
           "user_turns_with_marker": 0, "user_turns_total": 0, "partial_seen": False, "detail": []}
    if not os.path.isdir(d):
        return res
    full = sorted((int(m.group(2)), m.group(0)) for m in (RFULL.match(f) for f in os.listdir(d)) if m
                  and m.group(1) == side and i0 <= int(m.group(2)) <= i1)
    sidef = sorted((int(m.group(2)), m.group(0)) for m in (FNAME.match(f) for f in os.listdir(d)) if m
                   and m.group(1) == side and i0 <= int(m.group(2)) <= i1)
    files = full if full else sidef
    res["shape"] = "full" if full else ("side" if sidef else None)
    for idx, fn in files:
        blob = read_dump(d, fn)
        if blob is None:
            continue
        msgs, partial = msgs_of(blob)
        if not msgs:
            continue
        res["dumps_scanned"] += 1
        res["partial_seen"] = res["partial_seen"] or partial
        ui = first_user_idx(msgs)
        for k, m in enumerate(msgs):
            txt = content_of(m)
            if MARKER not in txt:
                continue
            if k == 0 and str(m.get("role")) == "system":
                res["marker_in_system"] = True
            if k <= 0 or (ui >= 0 and k < ui):
                res["marker_in_prefix"] = True
            if str(m.get("role")) == "user":
                res["marker_in_user"] = True
        for k, m in enumerate(msgs):
            if str(m.get("role")) == "user":
                res["user_turns_total"] += 1
                if MARKER in content_of(m):
                    res["user_turns_with_marker"] += 1
        res["detail"].append({"file": fn, "n_msgs": len(msgs), "partial": partial,
                              "marker_idx": [k for k, m in enumerate(msgs) if MARKER in content_of(m)][:3],
                              "roles": [str(m.get("role")) for m in msgs][:6]})
    res["verdict"] = bool(res["marker_in_user"] and not res["marker_in_prefix"]) if res["dumps_scanned"] else None
    return res


def cost(d, side, i0, i1):
    calls = p = c = comp = tot = unreported = 0
    models = set()
    for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        m = FNAME.match(fn)
        if not m or m.group(1) != side:
            continue
        idx = int(m.group(2))
        if idx < i0 or idx > i1:
            continue
        blob = read_dump(d, fn)
        if blob is None:
            continue
        calls += 1
        req = (blob.get("request") or {}).get("upstream_request") or {}
        if req.get("model"):
            models.add(str(req["model"]))
        u = (blob.get("response") or {}).get("usage") or {}
        if not u:
            unreported += 1
        p += int(u.get("prompt_tokens") or 0)
        comp += int(u.get("completion_tokens") or 0)
        tot += int(u.get("total_tokens") or 0)
        c += int((u.get("prompt_tokens_details") or {}).get("cached_tokens")
                 or u.get("prompt_cache_hit_tokens") or 0)
    return {"side": side, "range": [i0, i1], "calls": calls, "prompt_tokens": p, "cached_tokens": c,
            "completion_tokens": comp, "total_tokens": tot, "models": sorted(models),
            "unreported_usage": unreported}


def idx_ranges(D):
    out = {}
    p = os.path.join(D, "logs/idx.txt")
    if not os.path.isfile(p):
        return out
    for line in io.open(p, encoding="utf-8"):
        f = line.split()
        if len(f) == 3:
            out[f[0]] = [int(f[1]), int(f[2])]
    return out


def rc_of(D, arm, tid):
    p = os.path.join(D, arm, tid, "transcript.json")
    if not os.path.isfile(p):
        return {}
    try:
        d = json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return {}
    if isinstance(d, list):
        d = d[-1] if d else {}
    return {k: d.get(k) for k in ("rc", "role_note_chars", "prefix_sha256", "correctness_asserted",
                                  "self_test_met", "artifact_suspect", "steps") if k in d}


def cases_of(D, arm, tid):
    p = os.path.join(D, arm, tid, "cases.txt")
    if not os.path.isfile(p):
        return {"pass": 0, "total": 0, "rc": None}
    lines = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
    rc = None
    if lines and lines[-1].strip().isdigit():
        rc = int(lines[-1].strip())
        lines = lines[:-1]
    return {"pass": sum(1 for l in lines if l.startswith("CASE ") and l.strip().endswith("PASS")),
            "total": sum(1 for l in lines if l.startswith("CASE ")), "rc": rc}


def self_test():
    """机检: 旧缺陷复现(摘要 ⇒ 恒空) + 修复生效(裸数组 ⇒ 命中)。rc 0=两向都对。"""
    d539 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "r539/run-w1/adapter")
    ok = True
    if os.path.isdir(d539):
        side = json.load(io.open(os.path.join(d539, "side-agent-004.json"), encoding="utf-8"))
        m_side = msgs_of(side)
        old = [m for m in ((side.get("request") or {}).get("upstream_request") or {}).get("messages") or []]
        print("旧缺陷复现: side-* 摘要 -> 旧读数器得 %d 条消息; 新读数器得 %d 条 (partial=%s)"
              % (len(old), len(m_side[0]), m_side[1]))
        for k in ("side-agent-002.json",):
            pass
    full = os.path.join(d539, "full-agent-004.json")
    if os.path.isfile(full):
        fb = json.load(io.open(full, encoding="utf-8"))
        ms, part = msgs_of(fb)
        hit = any(MARKER in content_of(m) for m in ms)
        print("修复生效: full-* 裸数组 -> %d 条消息 (partial=%s), marker 命中=%s" % (len(ms), part, hit))
        ok = ok and hit and not part
    else:
        print("自检跳过 full-* (缺 %s)" % full)
    print("SELF-TEST", "OK" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", default=None)
    ap.add_argument("--window", default=None)
    ap.add_argument("--agents", default="R1r R1nr")
    ap.add_argument("--task-for", default="R1r:t1,R1nr:t1")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    D = a.run_dir
    R = os.path.dirname(os.path.abspath(D))
    W = a.window or os.path.basename(D).replace("run-", "")
    dumps = os.path.join(D, "adapter")
    rng = idx_ranges(D)
    out = {"round": "r540", "window": W, "run_dir": D, "arms": {}, "role_axis": {}, "deltas": {}}
    # 臂 -> (adapter side, tid)
    arms = {}
    for arm in a.agents.split():
        for tid in ("t1", "g1"):
            arms["%s-%s" % (arm, tid)] = ("agent", tid, arm)
    for k in ("A1-on-t1", "C-codex-t1"):
        if k in rng:
            arms[k] = ("agent" if k.startswith("A1") else "codex", "t1", k.split("-t1")[0])
    for name, (side, tid, arm) in arms.items():
        if name not in rng:
            continue
        i0, i1 = rng[name]
        out["arms"][name] = {"cost": cost(dumps, side, i0, i1), "cases": cases_of(D, arm, tid),
                             "rc": rc_of(D, arm, tid)}
        if arm in ("R1r", "R1nr") and tid == "t1":
            out["role_axis"][name] = role_mount_check(dumps, side, i0, i1)
    # 降幅 (同窗同题 t1)
    for base in ("A1-on-t1",):
        if base in out["arms"]:
            b = out["arms"][base]["cost"]
            for arm in ("R1r-t1", "R1nr-t1"):
                if arm in out["arms"]:
                    x = out["arms"][arm]["cost"]
                    out["deltas"]["%s_vs_%s" % (arm, base)] = {
                        "calls": x["calls"], "calls_base": b["calls"],
                        "calls_pct": (None if not b["calls"] else round(100.0 * (x["calls"] - b["calls"]) / b["calls"], 1)),
                        "total_tokens": x["total_tokens"], "total_tokens_base": b["total_tokens"],
                        "total_tokens_pct": (None if not b["total_tokens"] else round(100.0 * (x["total_tokens"] - b["total_tokens"]) / b["total_tokens"], 1)),
                        "cases_pass": out["arms"][arm]["cases"]["pass"], "cases_total": out["arms"][arm]["cases"]["total"],
                        "cases_pass_base": out["arms"][base]["cases"]["pass"]}
    p = os.path.join(D, "logs/analyze.json")
    json.dump(out, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ("window",)}, ensure_ascii=False))
    for k, v in sorted(out["arms"].items()):
        c, cs = v["cost"], v["cases"]
        print("臂 %-12s calls=%-3d total=%-7d cached=%-7d cases=%s/%s rc=%s"
              % (k, c["calls"], c["total_tokens"], c["cached_tokens"], cs["pass"], cs["total"], cs["rc"]))
    for k, v in sorted(out["role_axis"].items()):
        print("role轴 %-9s shape=%s scans=%d marker_in_user=%s in_prefix=%s partial=%s verdict=%s"
              % (k, v["shape"], v["dumps_scanned"], v["marker_in_user"], v["marker_in_prefix"],
                 v["partial_seen"], v["verdict"]))
    for k, v in sorted(out["deltas"].items()):
        print("降幅 %-18s calls %d vs %d (%s%%) tokens %d vs %d (%s%%) cases %s/%s vs base %s"
              % (k, v["calls"], v["calls_base"], v["calls_pct"], v["total_tokens"], v["total_tokens_base"],
                 v["total_tokens_pct"], v["cases_pass"], v["cases_total"], v["cases_pass_base"]))
    print("写出 " + p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
