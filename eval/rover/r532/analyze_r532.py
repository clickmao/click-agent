#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R532 迷你同窗对照 · 分析器 (只读跑盘, 不重算判分)。

三件事:
  ① **实发 prompt 机检 (挂载证明)**: 从 adapter 的 FULL dump 取 R1 臂首个请求的 system 轮,
     按 R522 纪律块标记切出 head —— head 须与**产品侧落盘的 prefix_sha256/prefix_chars**
     (transcript) **逐字节相等**; 且该纪律尾块须与同窗对侧臂(A1-on)**同一常量** (同 sha)。
     两条同时成立 ⇒ 线上恒定前缀 = head + 常量尾块, 随调用不变, 接线真实生效 (非"有代码行"自证)。
  ② 成本分列: 每臂 adapter range 内的调用数/tokens (usage_from_dumps, 中继实报)。
  ③ 质量分列: 隐藏用例脚本 stdout 的 CASE 行 (PASS/FAIL) + rc; 产物树清单。
输出 JSON 落盘 + 终端 ≤14 行摘要。
"""
from __future__ import annotations

# 宿主层 R522 纪律块起始标记 (常量尾块; 线上 system = R1 pin 前缀 + 本块)
DISC = "[上下文纪律 · 必守]"
import argparse, hashlib, json, os, subprocess, sys

REPO = "/home/agentuser/AgentFramework"
UFD = os.path.join(REPO, "eval/rover/r511/usage_from_dumps.py")


def usage(dump_dir, i0, i1, out_json):
    cmd = [sys.executable, UFD, "--dir", dump_dir, "--side", "agent",
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
    """取该臂首个请求: 优先 FULL dump (full-agent-NNN.json, 顶层=消息数组), 退 side dump。"""
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


def dig_system(req):
    """从 dump 里尽力取 system 文本 (兼容 顶层数组 / request.messages / request.body.messages)。"""
    if isinstance(req, list):
        msgs = req
    elif isinstance(req, dict):
        body = req.get("request") or req.get("body") or req.get("payload") or req
        msgs = body.get("messages") if isinstance(body, dict) else None
        if msgs is None and isinstance(body, dict) and isinstance(body.get("body"), dict):
            msgs = body["body"].get("messages")
    else:
        msgs = None
    if not isinstance(msgs, list):
        return None, []
    for m in msgs:
        if isinstance(m, dict) and m.get("role") == "system":
            return m.get("content"), msgs
    return None, msgs


def cases(path):
    txt = open(path, encoding="utf-8", errors="replace").read().splitlines()
    rc = None
    if txt and txt[-1].strip().isdigit():
        rc = int(txt[-1].strip())
        txt = txt[:-1]
    p = sum(1 for l in txt if l.strip().endswith("PASS"))
    f = sum(1 for l in txt if " FAIL " in (" " + l.strip() + " ") and "CASE" in l)
    return {"pass": p, "fail": f, "total": p + f, "rc": rc}


def artifacts(work, cap=40):
    out = []
    for root, dirs, files in os.walk(work):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for fn in files:
            fp = os.path.join(root, fn)
            out.append({"path": os.path.relpath(fp, work), "bytes": os.path.getsize(fp)})
    return sorted(out, key=lambda r: r["path"])[:cap]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--tid", default="t1")
    ap.add_argument("--window", default="mini1")
    a = ap.parse_args()
    D, tid = a.run_dir, a.tid
    res = {"window": a.window, "tid": tid, "run_dir": D, "arms": {}, "mount": {}, "boundaries": []}

    idx = {}
    for ln in open(os.path.join(D, "logs/idx.txt"), encoding="utf-8"):
        w = ln.split()
        if len(w) >= 3:
            idx[w[0]] = (int(w[1]), int(w[2]))
    for arm, (i0, i1) in idx.items():
        u, urc = usage(os.path.join(D, "adapter"), i0, i1, os.path.join(D, "logs/usage-%s.json" % arm))
        res["arms"][arm] = {"adapter_range": [i0, i1], "usage_rc": urc, "usage": u}

    # 质量
    for arm, cp in (("R1", os.path.join(D, "R1", tid, "cases.txt")),
                    ("A1-on", os.path.join(D, "A1-on", tid, "cases.txt"))):
        if os.path.exists(cp):
            res["arms"].setdefault(arm, {})["cases"] = cases(cp)
    rw = os.path.join(D, "R1", tid, "work")
    if os.path.exists(rw):
        res["arms"].setdefault("R1", {})["artifacts"] = artifacts(rw)
    aw = os.path.join(D, "A1-on", tid, "work")
    if os.path.exists(aw):
        res["arms"].setdefault("A1-on", {})["artifacts"] = artifacts(aw)

    # R1 落盘台账 (产品侧自报) —— 只作对照项, 不当挂载证明
    tp = os.path.join(D, "R1", tid, "transcript.json")
    if os.path.exists(tp):
        try:
            res["arms"]["R1"]["transcript"] = json.load(open(tp, encoding="utf-8"))
        except Exception as e:
            res["boundaries"].append("transcript 解析失败: %s" % e)
    else:
        res["boundaries"].append("transcript 未落盘 (文件缺) ⇒ prefix 自报项缺失")

    # 挂载证明: adapter dump 实发 system 轮 vs 产品侧 pin
    i0, i1 = idx.get("R1", (1, 0))
    ridx, req, kind = first_req(os.path.join(D, "adapter"), i0, i1)
    sys_txt, msgs = dig_system(req)
    side = {}
    sp = os.path.join(D, "adapter", "side-agent-%03d.json" % (ridx or 0))
    if os.path.exists(sp):
        try:
            sd = json.load(open(sp, encoding="utf-8"))
            up = (sd.get("request") or {}).get("upstream_request") or {}
            tms = up.get("tail_messages") or []
            sysm = [m for m in tms if m.get("role") == "system"]
            side = {
                "n_messages": (sd.get("request") or {}).get("n_messages"),
                "tools_n": (sd.get("request") or {}).get("tools_n"),
                "model": up.get("model"),
                "prompt_sha8": up.get("prompt_sha8"),
                "system_len": sysm[0].get("len") if sysm else None,
                "system_head": (sysm[0].get("head") or "")[:120] if sysm else None,
                "usage": (sd.get("response") or {}).get("usage"),
            }
        except Exception as e:
            res["boundaries"].append("side dump 解析失败: %s" % e)
    if sys_txt is None:
        res["boundaries"].append("adapter dump 中未解析出 system 轮 (形状不匹配) ⇒ 挂载证明未取到")
    else:
        tr = res["arms"].get("R1", {}).get("transcript") or {}
        pin_sha = (tr.get("prefix_sha256") or "")
        k = sys_txt.index(DISC) if DISC in sys_txt else -1
        head = sys_txt[:k].rstrip("\n") if k >= 0 else sys_txt
        suffix = sys_txt[k:] if k >= 0 else ""
        head_sha = hashlib.sha256(head.encode()).hexdigest()
        # 对侧 (A1-on) 同窗首请求里的同一块: 同 sha ⇒ 该尾块是**常量** (非随臂/随调用变化)
        a0, a1 = idx.get("A1-on", (1, 0))
        _, req2, _ = first_req(os.path.join(D, "adapter"), a0, a1)
        sys2, _ = dig_system(req2)
        other_same = None
        if isinstance(sys2, str) and DISC in sys2 and suffix:
            other_same = (sys2[sys2.index(DISC):] == suffix)
        res["mount"] = {
            "dump_index": ridx,
            "dump_kind": kind,
            # 线上恒定前缀 = head (须逐字节 == 台账 pin) + 宿主常量尾块 (R522 纪律)
            "head_chars": len(head),
            "head_sha256": head_sha,
            "head_equals_ledger_prefix": head_sha == pin_sha,
            "sent_system_chars": len(sys_txt),
            "sent_system_sha256": hashlib.sha256(sys_txt.encode()).hexdigest(),
            "recorded_prefix_chars": tr.get("prefix_chars"),
            "recorded_prefix_sha256": pin_sha,
            "host_suffix_chars": len(suffix),
            "host_suffix_sha256": hashlib.sha256(suffix.encode()).hexdigest() if suffix else None,
            "host_suffix_same_on_other_arm": other_same,
            "wire_prefix_chars": len(sys_txt),
            "wired_constant_prefix_ok": bool(head_sha == pin_sha and other_same is True),
            "messages": len(msgs or []),
            "roles": [m.get("role") for m in (msgs or []) if isinstance(m, dict)],
            "side": side,
        }
        if not (head_sha == pin_sha):
            res["boundaries"].append("实发 system 头部 != 台账 pin 前缀 ⇒ 恒定前缀不变量未成立")
        if other_same is not True:
            res["boundaries"].append("宿主尾块与对侧臂不一致 ⇒ 线上前缀并非同一常量 (cache 面可疑)")

    out = os.path.join(D, "logs/analysis-%s.json" % a.window)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=2)

    print("R532 分析 (window=%s, tid=%s)" % (a.window, tid))
    for arm in ("R1", "A1-on"):
        r = res["arms"].get(arm, {})
        u = r.get("usage") or {}
        c = r.get("cases") or {}
        print("  臂 %-6s calls=%s tokens=%s cases=%s/%s rc=%s files=%s range=%s"
              % (arm, u.get("calls"), u.get("total_tokens"), c.get("pass"), c.get("total"), c.get("rc"),
                 len(r.get("artifacts") or []), r.get("adapter_range")))
    m = res["mount"]
    print("  挂载证明: dump#%s 线上system=%s字符 | head=%s字符 sha=%s == 台账pin(%s字符 sha=%s)=%s | 宿主尾块=%s字符 sha=%s 与对侧同块=%s | msgs=%s tools_n=%s"
          % (m.get("dump_index"), m.get("sent_system_chars"), m.get("head_chars"),
             (m.get("head_sha256") or "")[:16], m.get("recorded_prefix_chars"),
             (m.get("recorded_prefix_sha256") or "")[:16], m.get("head_equals_ledger_prefix"),
             m.get("host_suffix_chars"), (m.get("host_suffix_sha256") or "")[:16],
             m.get("host_suffix_same_on_other_arm"), m.get("messages"), (m.get("side") or {}).get("tools_n")))
    print("  恒定前缀机检: wired_constant_prefix_ok=%s (线上前缀随调用不变, %s字符)"
          % (m.get("wired_constant_prefix_ok"), m.get("wire_prefix_chars")))
    if res["boundaries"]:
        for b in res["boundaries"]:
            print("  边界: %s" % b)
    print("  落盘: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
