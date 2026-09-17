#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R535 同窗对照 · 分析器 (只读跑盘, 不重算判分)。

五件事:
  ① **实发 prompt 机检 (挂载证明, R533 结构量轴)**: 从 adapter 的 FULL dump 取 R1 臂首个请求的
     system 轮 —— 须**逐字节 == 产品侧 pin** (本轮 R535 因契约渲染修复而 pin 上移: 3972 字符 / sha c40809b3…;
     旧值 3889/58e2df67 系 R532 时点) 且**不含** R522 纪律尾块;
     同请求 tools_n 须 == 0。三条同时成立 ⇒ 线上 system 就是恒定前缀本身 (非"有代码行"自证)。
  ② role 挂载证明: R1r 臂 user 轮须含 <role_profile> 且 transcript.role_note_chars > 0;
     同臂 system 前缀 sha 须与 R1nr 臂一致 (role 进 user 尾块, **不进**常量前缀 ⇒ 缓存面不受损)。
  ③ 台账透传: transcript completion/calls 与 adapter 中继 usage 对账 (R532 曾 completion 恒 0)。
  ④ 成本分列 / ⑤ 质量分列 (隐藏用例真跑 stdout 的 CASE 行 + rc) + 跨族读数。
输出 JSON 落盘 + 终端摘要。
"""
from __future__ import annotations

import argparse, hashlib, json, os, subprocess, sys

DISC = "[上下文纪律 · 必守]"          # R522 宿主常量尾块 (R533 起 R1 臂不应出现)
REPO = "/home/agentuser/AgentFramework"
UFD = os.path.join(REPO, "eval/rover/r511/usage_from_dumps.py")
ARMS = ("R1nr-t1", "R1r-t1", "R1r-m1", "R1r-g1", "A1-on-t1")


def usage(dump_dir, i0, i1, out_json, side="agent"):
    cmd = [sys.executable, UFD, "--dir", dump_dir, "--side", side,
           "--from", str(i0), "--to", str(i1), "--json", out_json]
    p = subprocess.run(cmd, capture_output=True, text=True)
    u = {}
    if os.path.exists(out_json):
        try:
            u = json.load(open(out_json, encoding="utf-8"))
        except Exception:
            u = {}
    return u, p.returncode


def first_req(dump_dir, i0, i1):
    for i in range(i0, i1 + 1):
        for pat in ("full-agent-%03d.json", "side-agent-%03d.json"):
            p = os.path.join(dump_dir, pat % i)
            if not os.path.exists(p):
                continue
            try:
                return i, json.load(open(p, encoding="utf-8")), pat.split("-")[0]
            except Exception:
                continue
    return None, None, None


def dig_msgs(req):
    if isinstance(req, list):
        msgs = req
    elif isinstance(req, dict):
        body = req.get("request") or req.get("body") or req.get("payload") or req
        msgs = body.get("messages") if isinstance(body, dict) else None
        if msgs is None and isinstance(body, dict) and isinstance(body.get("body"), dict):
            msgs = body["body"].get("messages")
    else:
        msgs = None
    return msgs if isinstance(msgs, list) else []


def sys_of(msgs):
    for m in msgs:
        if isinstance(m, dict) and m.get("role") == "system":
            return m.get("content")
    return None


def user_of(msgs):
    for m in msgs:
        if isinstance(m, dict) and m.get("role") == "user":
            return m.get("content")
    return None


def cases(path):
    txt = open(path, encoding="utf-8", errors="replace").read().splitlines()
    rc = None
    if txt and txt[-1].strip().isdigit():
        rc = int(txt[-1].strip())
        txt = txt[:-1]
    p = sum(1 for l in txt if l.startswith("CASE ") and l.strip().endswith("PASS"))
    f = sum(1 for l in txt if l.startswith("CASE ") and " FAIL " in l)
    return {"pass": p, "fail": f, "total": p + f, "rc": rc}


def artifacts(work, cap=40):
    out = []
    for root, dirs, files in os.walk(work):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for fn in files:
            fp = os.path.join(root, fn)
            out.append({"path": os.path.relpath(fp, work), "bytes": os.path.getsize(fp)})
    return sorted(out, key=lambda r: r["path"])[:cap]


def side_dump(dump_dir, idx):
    p = os.path.join(dump_dir, "side-agent-%03d.json" % (idx or 0))
    if not os.path.exists(p):
        return {}
    try:
        sd = json.load(open(p, encoding="utf-8"))
    except Exception:
        return {}
    req = sd.get("request") or {}
    up = req.get("upstream_request") or {}
    tms = up.get("tail_messages") or []
    sysm = [m for m in tms if isinstance(m, dict) and m.get("role") == "system"]
    return {"n_messages": req.get("n_messages"), "tools_n": req.get("tools_n"),
            "model": up.get("model"), "prompt_sha8": up.get("prompt_sha8"),
            "system_len": sysm[0].get("len") if sysm else None,
            "usage": (sd.get("response") or {}).get("usage")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--window", default="w1")
    a = ap.parse_args()
    D = a.run_dir
    res = {"window": a.window, "run_dir": D, "arms": {}, "mount": {}, "role_mount": {},
           "boundaries": [], "pin": {}}

    idx = {}
    ip = os.path.join(D, "logs/idx.txt")
    if os.path.isfile(ip):
        for ln in open(ip, encoding="utf-8"):
            w = ln.split()
            if len(w) >= 3:
                idx[w[0]] = (int(w[1]), int(w[2]))

    for arm, (i0, i1) in idx.items():
        u, urc = usage(os.path.join(D, "adapter"), i0, i1, os.path.join(D, "logs/usage-%s.json" % arm))
        res["arms"][arm] = {"adapter_range": [i0, i1], "usage_rc": urc, "usage": u}

    for arm in ARMS:
        tid = arm.split("-")[-1]
        base = os.path.join(D, arm.replace("-" + tid, ""), tid)
        cp = os.path.join(base, "cases.txt")
        if os.path.isfile(cp):
            res["arms"].setdefault(arm, {})["cases"] = cases(cp)
        wk = os.path.join(base, "work")
        if os.path.isdir(wk):
            res["arms"].setdefault(arm, {})["artifacts"] = artifacts(wk)
        tp = os.path.join(base, "transcript.json")
        if os.path.isfile(tp):
            try:
                tr = json.load(open(tp, encoding="utf-8"))
                res["arms"].setdefault(arm, {})["transcript"] = tr
                res["pin"] = {"prefix_chars": tr.get("prefix_chars"),
                              "prefix_sha256": tr.get("prefix_sha256")}
            except Exception as e:
                res["boundaries"].append("%s transcript 解析失败: %s" % (arm, e))

    # --- ① 实发 prompt 机检 (R1 主管道臂 R1r-t1) ---
    pin_chars = res["pin"].get("prefix_chars")
    pin_sha = res["pin"].get("prefix_sha256")
    i0, i1 = idx.get("R1r-t1", (1, 0))
    ridx, req, kind = first_req(os.path.join(D, "adapter"), i0, i1)
    msgs = dig_msgs(req)
    sys_txt = sys_of(msgs)
    sd = side_dump(os.path.join(D, "adapter"), ridx)
    if sys_txt is None:
        res["boundaries"].append("adapter dump 未解析出 R1r-t1 的 system 轮 ⇒ 挂载证明未取到")
    else:
        sha = hashlib.sha256(sys_txt.encode()).hexdigest()
        res["mount"] = {
            "dump_index": ridx, "dump_kind": kind,
            "sent_system_chars": len(sys_txt), "sent_system_sha256": sha,
            "recorded_prefix_chars": pin_chars, "recorded_prefix_sha256": pin_sha,
            "system_equals_pin": bool(sha == pin_sha and len(sys_txt) == pin_chars),
            "discipline_block_present": DISC in sys_txt,
            "tools_n": sd.get("tools_n"), "n_messages": sd.get("n_messages"),
            "model": sd.get("model"),
            "system_chars_from_side": sd.get("system_len"),
            "roles": [m.get("role") for m in msgs if isinstance(m, dict)],
            "wired_clean_prefix_ok": bool(sha == pin_sha and len(sys_txt) == pin_chars
                                          and DISC not in sys_txt and (sd.get("tools_n") in (0, None))),
        }
        if sha != pin_sha:
            res["boundaries"].append("实发 system != 台账 pin 前缀 ⇒ 恒定前缀不变量未成立")
        if DISC in sys_txt:
            res["boundaries"].append("实发 system 仍含 R522 纪律尾块 ⇒ 结构量轴未生效")
        if sd.get("tools_n") not in (0, None):
            res["boundaries"].append("实发 tools_n=%s ≠ 0 ⇒ 模型侧仍有工具面" % sd.get("tools_n"))

    # --- ② role 挂载证明 (R1r-t1 vs R1nr-t1) ---
    rm = {}
    for arm, rid in (("R1r-t1", idx.get("R1r-t1")), ("R1nr-t1", idx.get("R1nr-t1"))):
        if not rid:
            continue
        ix, rq, _ = first_req(os.path.join(D, "adapter"), rid[0], rid[1])
        m2 = dig_msgs(rq)
        s2 = sys_of(m2)
        u2 = user_of(m2) or ""
        tr = (res["arms"].get(arm, {}) or {}).get("transcript") or {}
        rm[arm] = {"transcript_role_note_chars": tr.get("role_note_chars"),
                   "user_has_role_block": ("<role_profile>" in u2),
                   "user_chars": len(u2),
                   "system_sha256": hashlib.sha256(s2.encode()).hexdigest() if isinstance(s2, str) else None}
    if "R1r-t1" in rm and "R1nr-t1" in rm:
        rm["role_in_user_tail_only_ok"] = bool(
            rm["R1r-t1"]["user_has_role_block"] and not rm["R1nr-t1"]["user_has_role_block"]
            and rm["R1r-t1"]["system_sha256"] == rm["R1nr-t1"]["system_sha256"]
            and (rm["R1r-t1"]["transcript_role_note_chars"] or 0) > 0
            and (rm["R1nr-t1"]["transcript_role_note_chars"] or 0) == 0)
        if not rm["role_in_user_tail_only_ok"]:
            res["boundaries"].append("role 挂载机检未全过 (见 role_mount)")
    res["role_mount"] = rm

    out = os.path.join(D, "logs/analysis-%s.json" % a.window)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=2)

    print("R535 分析 (window=%s)" % a.window)
    base = None
    for arm in ARMS:
        r = res["arms"].get(arm, {})
        u = r.get("usage") or {}
        c = r.get("cases") or {}
        tr = r.get("transcript") or {}
        print("  臂 %-8s range=%-9s calls=%-3s tok=%-8s cases=%s/%s rc=%s exec_rep=%s R1rc=%s"
              % (arm, str(r.get("adapter_range")), u.get("calls"), u.get("total_tokens"),
                 c.get("pass"), c.get("total"), c.get("rc"), tr.get("exec_repairs"), tr.get("rc")))
    if base is None:
        a1 = (res["arms"].get("A1-on-t1", {}) or {}).get("usage") or {}
        r1 = (res["arms"].get("R1r-t1", {}) or {}).get("usage") or {}
        if a1.get("calls") and r1.get("calls"):
            print("  同题 t1 判据: calls %s → %s (%.3f×) ; tokens %s → %s (%.3f×) ⇒ 降幅 %.1f%%"
                  % (a1.get("calls"), r1.get("calls"), r1["calls"] / a1["calls"],
                     a1.get("total_tokens"), r1.get("total_tokens"),
                     r1["total_tokens"] / a1["total_tokens"],
                     100.0 * (1 - r1["total_tokens"] / a1["total_tokens"])))
    m = res["mount"]
    print("  挂载证明: dump#%s 线上system=%s字符 sha=%s == pin(%s字符 %s)=%s | 纪律尾块在场=%s | tools_n=%s | msgs=%s model=%s"
          % (m.get("dump_index"), m.get("sent_system_chars"), (m.get("sent_system_sha256") or "")[:16],
             m.get("recorded_prefix_chars"), (m.get("recorded_prefix_sha256") or "")[:16],
             m.get("system_equals_pin"), m.get("discipline_block_present"), m.get("tools_n"),
             m.get("n_messages"), m.get("model")))
    print("  恒定前缀机检: wired_clean_prefix_ok=%s" % m.get("wired_clean_prefix_ok"))
    print("  role 挂载: %s" % json.dumps(res["role_mount"], ensure_ascii=False))
    lt = (res["arms"].get("R1r-t1", {}) or {}).get("transcript") or {}
    ua = (res["arms"].get("A1-on-t1", {}) or {}).get("usage") or {}
    if lt and ua:
        print("  台账透传: transcript calls=%s prompt=%s completion=%s | adapter calls=%s total=%s"
              % (lt.get("calls"), lt.get("prompt_tokens"), lt.get("completion_tokens"),
                 ua.get("calls"), ua.get("total_tokens")))
    for b in res["boundaries"]:
        print("  边界: %s" % b)
    print("  落盘: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
