#!/usr/bin/env python3
"""R485 微问询形态分流闸 — 离线器具 (H1 机检 + H4 负控 + 离线投影)。

口径/纪律 (预注册 prereg_r485.json 对齐):
  * 回指标记表**从 C# 源码派生** (单一事实源: src/agent.exploration/MicroStepIsolationGate.cs),
    取不到 / 表为空 / 缺关键标记 ⇒ rc=3 **弃权** (fail-closed, 不冒充读数);
  * 语料为**已提交产物** (eval/rover/r482/{calls,usage}-{Arole,R}.jsonl), 只读, 不重跑真链;
  * 离线投影 ≠ 真机读数; 两者分列, 不混算 (本器具只产离线面);
  * token 缺失 ⇒ 记 unreported (**禁冒充 0**); 只在逐调用 usage 齐备时才给投影;
  * 负控: --nc-selfcontained (自足问句不得被拦) / --nc-empty-markers (空表 ⇒ 0 拦截 且 rc!=0)。

用法:
  python3 eval/rover/r485/gate_probe.py
  python3 eval/rover/r485/gate_probe.py --nc-selfcontained
  python3 eval/rover/r485/gate_probe.py --nc-empty-markers
"""
import argparse
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
GATE_SRC = os.path.join(ROOT, "src", "agent.exploration", "MicroStepIsolationGate.cs")
MICRO_PREFIX = "[微步骤隔离问询]"
ARMS = {"Arole": "Arole", "R": "R"}

# 负控用自足问句 (与单测同族; 合成样本, 不冒充录制流量)
SELF_CONTAINED = [
    "把构建命令写成一行。",
    "计算 3 加 5 的结果",
    "列出 .NET 10 的三个新特性",
    "解释递归与迭代的区别",
]

RC_OK, RC_NEGFAIL, RC_ABSTAIN = 0, 2, 3


def derive_markers():
    """从 C# 源码派生标记表 (单一事实源); 失败返回 None。"""
    try:
        src = open(GATE_SRC, encoding="utf-8").read()
    except OSError as e:
        print(f"[abstain] 无法读闸源码 {GATE_SRC}: {e}")
        return None
    m = re.search(r"AnaphoraMarkers\s*=\s*new\s+string\[\]\s*\{(.*?)\}\s*;", src, re.S)
    if not m:
        print("[abstain] 源码内未找到 AnaphoraMarkers 数组字面量")
        return None
    return re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))


def decide(q, markers):
    """与 C# Decide 同构的移植 (权限: blank > marker > send)。"""
    s = "" if q is None else q
    if s.strip() == "":
        return "blank", ""
    for mk in markers:
        if mk and mk in s:
            return "isolation_invalid_anaphora", mk
    return "ok", ""


def load_jsonl(path):
    if not os.path.exists(path):
        return None
    out = []
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            if line.strip():
                out.append(json.loads(line))
    return out


def find_key(obj, key):
    """递归找首个同名字段 (usage 结构跨供应商不一致时的容错读取)。"""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = find_key(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_key(v, key)
            if r is not None:
                return r
    return None


def micro_question(msgs):
    """返回 (is_micro, 微问题原文)。仅看首条 user 消息 (与产品包裹形态一致)。"""
    for m in msgs:
        c = m.get("content") or ""
        if MICRO_PREFIX in c:
            s = c.split(MICRO_PREFIX, 1)[1].lstrip()
            return True, s.split("\n", 1)[0].strip()
    return False, ""


def classify_arm(arm, markers):
    calls = load_jsonl(os.path.join(ROOT, "eval", "rover", "r482", f"calls-{ARMS[arm]}.jsonl"))
    usage = load_jsonl(os.path.join(ROOT, "eval", "rover", "r482", f"usage-{ARMS[arm]}.jsonl"))
    if calls is None:
        return None
    tok_by_seq, unreported = {}, []
    for row in usage or []:
        seq = row.get("seq")
        t = find_key(row, "total_tokens")
        if seq is None:
            continue
        if isinstance(t, int):
            tok_by_seq[seq] = tok_by_seq.get(seq, 0) + t
        else:
            unreported.append(seq)

    res = {"calls": len(calls), "micro": 0, "micro_blocked": 0, "main": 0, "main_blocked": 0,
           "blocked_seqs": [], "markers_hit": {}, "tok_blocked": 0, "tok_total": 0,
           "usage_rows": len(usage or []), "tok_unreported_seqs": unreported}
    for row in calls:
        msgs = row.get("messages") or []
        seq = row.get("seq")
        is_micro, q = micro_question(msgs)
        reason, marker = decide(q, markers)
        t = tok_by_seq.get(seq)
        if isinstance(t, int):
            res["tok_total"] += t
        if is_micro:
            res["micro"] += 1
            if reason != "ok":
                res["micro_blocked"] += 1
                res["blocked_seqs"].append(seq)
                res["markers_hit"][marker] = res["markers_hit"].get(marker, 0) + 1
                if isinstance(t, int):
                    res["tok_blocked"] += t
        else:
            res["main"] += 1
            q_main = (msgs[1].get("content") if len(msgs) > 1 else "") or ""
            if decide(q_main, markers)[0] != "ok":
                res["main_blocked"] += 1
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nc-selfcontained", action="store_true")
    ap.add_argument("--nc-empty-markers", action="store_true")
    args = ap.parse_args()

    markers = derive_markers()
    if markers is None:
        print("rc=3 弃权 (标记表不可派生)")
        return RC_ABSTAIN
    if len(markers) == 0 or "上一条" not in markers:
        print(f"rc=3 弃权 (标记表可疑: n={len(markers)})")
        return RC_ABSTAIN
    if args.nc_empty_markers:
        markers = []
    print(f"标记表 (源码派生) n={len(markers)}: {markers}")

    body = {"gate_src": os.path.relpath(GATE_SRC, ROOT), "markers": markers,
            "corpus": "eval/rover/r482/{calls,usage}-{Arole,R}.jsonl (已提交产物)", "arms": {}}
    assert_ok = True
    for arm in ARMS:
        r = classify_arm(arm, markers)
        if r is None:
            print(f"[{arm}] 语料缺失 ⇒ 弃权")
            return RC_ABSTAIN
        body["arms"][arm] = r
        pct_calls = 100.0 * r["micro_blocked"] / r["calls"] if r["calls"] else 0.0
        pct_tok = 100.0 * r["tok_blocked"] / r["tok_total"] if r["tok_total"] else 0.0
        print(f"[{arm}] calls={r['calls']} micro={r['micro']} blocked={r['micro_blocked']} "
              f"main={r['main']} main_blocked={r['main_blocked']} "
              f"tok_total={r['tok_total']} tok_blocked={r['tok_blocked']} "
              f"(调用 {pct_calls:.1f}% / token {pct_tok:.2f}%) unreported={r['tok_unreported_seqs']}")

    # --- 负控 ---
    nc = {}
    if args.nc_empty_markers:
        blocked = sum(a["micro_blocked"] for a in body["arms"].values())
        print(f"[nc-empty-markers] 空标记表 ⇒ 拦截数={blocked} (必须为 0) ; 表空 ⇒ 闸失效, 器具弃权 rc=3")
        return RC_ABSTAIN

    if args.nc_selfcontained:
        hits = [q for q in SELF_CONTAINED if decide(q, markers)[0] != "ok"]
        main_blocked = sum(a["main_blocked"] for a in body["arms"].values())
        nc = {"synthetic_self_contained": len(SELF_CONTAINED), "synthetic_blocked": len(hits),
              "recorded_main_blocked": main_blocked}
        print(f"[nc-selfcontained] 合成自足问句 {len(SELF_CONTAINED)} 条被拦 {len(hits)} ; "
              f"录制主组被拦 {main_blocked}")
        if hits or main_blocked:
            print("rc=2 负控失败 (误伤)")
            return RC_NEGFAIL
        print("rc=0 负控通过")
        return RC_OK

    # --- H1 判据 (机检, 只对 Arole 主 pin 断言) ---
    a = body["arms"]["Arole"]
    h1 = {"skip_micro": a["micro_blocked"], "skip_micro_expected": a["micro"],
          "skip_main": a["main_blocked"], "calls": a["calls"]}
    body["h1"] = h1
    if a["micro"] != 7 or a["calls"] != 21:
        print(f"rc=3 弃权: pin 形状漂移 (micro={a['micro']} calls={a['calls']}, 期望 7/21)")
        return RC_ABSTAIN
    assert_ok = (a["micro_blocked"] == 7 and a["main_blocked"] == 0)
    body["h1_verdict"] = "PASS" if assert_ok else "FAIL"
    body["projection_offline"] = {
        "note": "离线投影 (只读已录制 usage) ≠ 真机重跑; 两条臂口径分列, 不混算",
        "Arole": {"call_cut": f"{a['micro_blocked']}/{a['calls']}",
                  "call_cut_pct": round(100.0 * a["micro_blocked"] / a["calls"], 2),
                  "tok_cut": a["tok_blocked"], "tok_total": a["tok_total"],
                  "tok_cut_pct": round(100.0 * a["tok_blocked"] / a["tok_total"], 2)},
    }
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    body["sha16"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    out = os.path.join(HERE, "h1_gate_readings.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(body, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    print(f"H1 {'PASS' if assert_ok else 'FAIL'} (skip_micro={a['micro_blocked']}/{a['micro']}, "
          f"skip_main={a['main_blocked']}) sha16={body['sha16']}")
    print(f"读数已写: {os.path.relpath(out, ROOT)}")
    return RC_OK if assert_ok else RC_NEGFAIL


if __name__ == "__main__":
    sys.exit(main())
