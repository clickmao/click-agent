#!/usr/bin/env python3
"""R491 判据器派生器 (R488 教训: 判据器由上一轮机派生, 禁手抄)。

自 r490/analyze_r490.py 派生 r491/analyze_r491.py: 命名空间改写 + 臂计划改为
Aroleb/T1/T2/T3 + 未跑臂不静默豁免 (blocking=True) + T 三跑离散度 (下界) + ③④ 面。
锚点缺失即非零退出。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "r490", "analyze_r490.py")
DST = os.path.join(HERE, "analyze_r491.py")

RENAMES = [("analyze_r490", "analyze_r491"), ("r490", "r491"), ("R490", "R491")]

# (旧, 新) —— 每条必须命中且仅命中 1 次, 否则非零退出
PATCHES = [
    ('    out = {"round": "R491", "arms": {}, "invariants": [], "deltas": {}, "cross_round_ref": {}}',
     '''    out = {"round": "R491", "arms": {}, "invariants": [], "deltas": {}, "cross_round_ref": {}}
    out["pair_face"] = {k: pair_face(k) for _, k in ARMS}
    out["deadcode_face"] = deadcode_face(os.path.abspath(os.path.join(HERE, "..", "..", "..")))'''),

    ('ARMS = [("B", "Aroleb"), ("R", "R1"), ("T1", "T1"), ("T2", "T2")]',
     'ARMS = [("B", "Aroleb"), ("T1", "T1"), ("T2", "T2"), ("T3", "T3")]  # R491: R 臂本轮未跑'),

    ('    for arm in ("R", "T1", "T2"):',
     '    for arm in ("T1", "T2", "T3"):'),

    ('''    if not (out["arms"]["R"].get("not_run") or out["arms"]["T1"].get("not_run")):
        out["deltas"]["T1_vs_R"] = {
            "calls": out["arms"]["R"]["calls"] - out["arms"]["T1"]["calls"],
            "total_tokens": out["arms"]["R"]["total"] - out["arms"]["T1"]["total"],
            "pct": pct(out["arms"]["T1"]["total"], out["arms"]["R"]["total"]),
        }''',
     '''    ran = [x for x in ("T1", "T2", "T3") if not out["arms"][x].get("not_run")]
    if ran:
        tot = [out["arms"][x]["total"] for x in ran]
        cal = [out["arms"][x]["calls"] for x in ran]
        out["deltas"]["T_spread"] = {
            "arms": ran,
            "total_tokens": "%d..%d (min..max)" % (min(tot), max(tot)),
            "calls": "%d..%d" % (min(cal), max(cal)),
            "pct_vs_B": "%s..%s" % (pct(min(tot), B["total"]), pct(max(tot), B["total"])),
            "worst_case_total_pct": pct(max(tot), B["total"]),
        }'''),

    ('''            out["invariants"].append({"id": "I0_臂可跑", "arm": arm, "pass": False, "blocking": False,
                                      "evidence": a["reason"]})''',
     '''            out["invariants"].append({"id": "I0_臂可跑", "arm": arm, "pass": False,
                                      "blocking": arm not in OUT_OF_SCOPE,
                                      "evidence": a["reason"]})
            out.setdefault("unreported_planned_arms", []).append(arm)'''),
]

PRELUDE = '''
# R491: 计划内未跑臂的显式声明 (空 = 计划全跑; 未跑即 FAIL, 禁静默豁免)
OUT_OF_SCOPE = {}
'''

EXTRA = '''

# ══════════════════════════════════════════════════════════════════════════
# R491 追加面 (派生器注入; 与 R490 面并存, 不改旧判据语义)
# ══════════════════════════════════════════════════════════════════════════

def _msgs(c):
    """R491 修: 实发 messages 在 calls-*.jsonl **顶层** (R490 的 pair 面误取 request.messages)。"""
    return c.get("messages") or ((c.get("request") or {}).get("messages")) or []


def pair_face(key):
    """候选③ 面: 零远端调用轮的 user 侧是否也在回放里 (闸关应 >0, 闸开应 =0)。"""
    calls = rows(os.path.join(HERE, "calls-%s.jsonl" % key))
    adj = leak = 0
    for c in calls:
        msgs = _msgs(c)
        roles = [m.get("role") for m in msgs]
        for i in range(1, len(roles)):
            if roles[i - 1] == "user" and roles[i] == "user":
                adj += 1
        for m in msgs:
            if m.get("role") == "user" and TEMPLATE in (m.get("content") or ""):
                leak += 1
    telem = rows(os.path.join(HERE, "tel-%s" % key, "host.jsonl"))
    gate = [r for r in telem if r.get("point") == "tool_decl_gate"]
    ut = sum(int((r.get("kv") or {}).get("replay_user_trimmed") or 0) for r in gate)
    pg = sorted({str((r.get("kv") or {}).get("replay_pair_gate")) for r in gate})
    return {"user_trimmed": ut, "pair_gate": pg or ["(none)"], "user_user_adj": adj, "skip_user_leak": leak}


def deadcode_face(root):
    """候选④ 面: R479 三件产物在链上的引用计数 (源码面, 排 bin/obj)。0 生产引用 ⇒ 不在链上。"""
    import subprocess
    out = {}
    for s in ("ResponsesWire", "LocalDecisionMap", "ActionToolSpec"):
        raw = subprocess.run(["grep", "-rn", r"\\b%s\\b" % s, "--include=*.cs", "src/"],
                             cwd=root, capture_output=True, text=True).stdout
        prod, test = [], []
        for line in raw.splitlines():
            p = line.split(":", 1)[0]
            if "/bin/" in p or "/obj/" in p:
                continue
            (test if "/agent.tests/" in p else prod).append(p)
        out[s] = {"prod": len(prod), "test": len(test), "files": sorted(set(prod))}
    return out
'''


def apply_patches(body):
    for old, new in PATCHES:
        n = body.count(old)
        if n != 1:
            print("[derive-analyzer] FATAL 补丁命中 %d 次 (须 1): %r" % (n, old[:60]), file=sys.stderr)
            return None
        body = body.replace(old, new, 1)
    return body


def main():
    src = open(SRC, encoding="utf-8").read()
    if "def main()" not in src or src.count("r490") == 0:
        print("[derive-analyzer] FATAL 源锚点缺失", file=sys.stderr)
        return 2
    body = src
    counts = {}
    for old, new in RENAMES:
        counts[old] = body.count(old)
        body = body.replace(old, new)
    body = apply_patches(body)
    if body is None:
        return 2
    body = body.replace("def main():", PRELUDE + EXTRA + "\n\ndef main():", 1)
    open(DST, "w", encoding="utf-8").write(body)
    print("[derive-analyzer] 改写计数:", counts)
    import py_compile
    py_compile.compile(DST, doraise=True)
    txt = open(DST, encoding="utf-8").read()
    for must in ("def pair_face(", "def deadcode_face(", "OUT_OF_SCOPE", "T_spread",
                 '("T3", "T3")', "replay_user_trimmed"):
        if must not in txt:
            print("[derive-analyzer] FATAL 派生物缺锚点: " + must, file=sys.stderr)
            return 2
    print("[derive-analyzer] 形式门禁 PASS (可编译 + 臂计划/豁免/离散度/③④ 面在位)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
