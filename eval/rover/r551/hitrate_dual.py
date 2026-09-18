#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R551 适配版(基于 R550 候选② 逐字复制): 增补可选 --wins 显式窗号列。

R551 差异声明: 唯一改动 = 窗号列参数化 (attribute/run 增 wins 形参 + --wins); 缺省路径与
R550 版逐位同 (以 R550 既有数据 regression 复算为证)。原: R550 候选②：**命中率口径脚本化重钉**（per-call 中继 usage，双口径并列）。

背景（R549 §7）：R548 报告里的「命中率行」在穷举自明口径下**无一可复现**（最接近的拟合是
「末次调用 miss ÷ 前缀**字符**数」，该口径未在报告写明且与首调用读数冲突）⇒ 该行已被裁定
**不得作验收依据**。本脚本把口径钉成**可复算的代码**，从此每个读数都带口径名与单位。

口径（单位一律写进字段名；禁用名义总量 `total_tokens`）：
  v_all          = 1 − Σ miss_tok / Σ prompt_tok          含冷启动（第 1 次调用必然低）
  v_incr         = 1 − miss_tok(末次调用) / prompt_tok(末次调用)   仅增量面（会话第 ≥2 次）
  v_prefix_chars = 1 − miss_tok(末次) / prefix_chars        分母是**字符**不是 token
                   ⇒ unit_mismatch=True，**只作口径错示例登记, 不作读数**（R548 报告值的疑似来源）

铁律：
  ① 逐调用恒等式 `prompt_tok == hit_tok + miss_tok`；违反 ⇒ **rc=2 器具缺陷**（禁计入被测读数）；
  ② 缺 usage 记哨兵 `-1` 并从比率中**剔除** + 单列计数（禁按 0 计入）；
  ③ 双路交叉校验：dump 求和 vs transcript 自报 `cache_hit_tokens/cache_miss_tokens`，不符 ⇒ 报警
     （报警不阻断, 但当轮读数须带 `xref_dump_vs_transcript=False`）；
  ④ 窗口↔调用映射 = **中继 dump 落盘时间轴**（权威外部真值）; 若 Σtranscript.calls ≠ dump 数
     ⇒ 记 `count_mismatch`（自报低估: R550 实测契约重试循环未计入, 2 vs 4）。

用法：
  python3 hitrate_dual.py --dumps /tmp/r548_c2/adapter --run-dir /tmp/r548_c2 --arm R548b
  python3 hitrate_dual.py --selftest            # 三态自检（正常/恒等式错/未上报）
退出码：0 = 全部可判 / 1 = 有窗口不可判（缺 dump/无 usage）/ 2 = 器具缺陷（恒等式违反）/ 3 = 输入缺失
"""
import argparse
import glob
import io
import json
import os
import sys

IDENTITY_KEYS = ("prompt_tokens", "completion_tokens", "prompt_cache_hit_tokens", "prompt_cache_miss_tokens")


def load(p):
    with io.open(p, encoding="utf-8-sig", errors="replace") as fh:
        return json.load(fh)


def usage_of(dump):
    """取中继 usage（缺 ⇒ 全 None = unreported 哨兵路径）。"""
    u = ((dump.get("response") or {}).get("usage")) or {}
    out = {k: u.get(k) for k in IDENTITY_KEYS}
    out["_reported"] = any(u.get(k) is not None for k in ("prompt_tokens", "prompt_cache_hit_tokens",
                                                         "prompt_cache_miss_tokens"))
    return out


def identity_violation(u):
    """① 恒等式；缺项不算违反（缺项走未上报路径）。"""
    p, h, m = u.get("prompt_tokens"), u.get("prompt_cache_hit_tokens"), u.get("prompt_cache_miss_tokens")
    if p is None or h is None or m is None:
        return None
    return None if p == h + m else {"prompt_tokens": p, "hit": h, "miss": m, "delta": p - (h + m)}


def hitrate(calls, prefix_chars=None):
    """calls = [usage,...] 按调用顺序。返回三口径 + 完整性问题清单。"""
    rep = [u for u in calls if u.get("_reported")]
    unreported = len(calls) - len(rep)
    rec = {"calls": len(calls), "calls_reported": len(rep), "unreported": unreported,
           "v_all": -1.0, "v_incr": -1.0, "v_prefix_chars": -1.0,
           "sum_prompt_tok": None, "sum_miss_tok": None, "sum_hit_tok": None,
           "last_prompt_tok": None, "last_miss_tok": None, "prefix_chars": prefix_chars,
           "unit_mismatch_v_prefix_chars": True, "problems": []}
    if not rep:
        rec["problems"].append("no_reported_usage")
        return rec
    sp = sum(u["prompt_tokens"] or 0 for u in rep)
    sm = sum(u["prompt_cache_miss_tokens"] or 0 for u in rep)
    sh = sum(u["prompt_cache_hit_tokens"] or 0 for u in rep)
    last = rep[-1]
    rec.update({"sum_prompt_tok": sp, "sum_miss_tok": sm, "sum_hit_tok": sh,
                "last_prompt_tok": last["prompt_tokens"], "last_miss_tok": last["prompt_cache_miss_tokens"]})
    rec["v_all"] = round(1.0 - sm / sp, 4) if sp else -1.0          # 含冷启动
    lp, lm = last["prompt_tokens"], last["prompt_cache_miss_tokens"]
    rec["v_incr"] = round(1.0 - lm / lp, 4) if (lp and lm is not None) else -1.0   # 仅增量面
    if prefix_chars:
        rec["v_prefix_chars"] = round(1.0 - lm / prefix_chars, 4)                  # 口径错示例: 单位不一致
    if unreported:
        rec["problems"].append("unreported_usage_excluded:%d" % unreported)
    return rec


def attribute(files, run_dir, nwin=3, wins=None):
    """窗口↔dump 归属：**中继 dump 落盘时间轴**为外部真值（transcript.calls 在契约重试窗会低估）。

    规则：把每个 dump 归给「其落盘时刻之后**最早**的窗 transcript」；同一窗内按落盘序。返回
    [(win, [usage...], attribution_note)]，并单列 count_mismatch（Σcalls vs dump 数）。
    """
    ids = list(wins) if wins else list(range(1, nwin + 1))
    tpairs = []
    for w in ids:
        tp = os.path.join(run_dir, "r1_%d" % w, "transcript.json")
        if os.path.isfile(tp):
            tpairs.append((w, os.path.getmtime(tp), os.path.getsize(tp), tp))
    tpairs.sort(key=lambda x: x[1])
    buckets = {w: [] for w, _, _, _ in tpairs}
    unassigned = []
    for f in files:
        mt = os.path.getmtime(f)
        cand = [w for w, t, _, _ in tpairs if t >= mt - 1]
        if not cand:
            unassigned.append(f)
            continue
        buckets[cand[0]].append(f)
    return buckets, [w for w, _, _, _ in tpairs], unassigned


def run(dumps_dir, run_dir, arm, nwin=3, wins=None):
    files = sorted(glob.glob(os.path.join(dumps_dir, "side-agent-*.json")))
    buckets, wids, unassigned = attribute(files, run_dir, nwin, wins)
    viol = [(os.path.basename(f), identity_violation(usage_of(load(f)))) for f in files]
    viol = [(f, v) for f, v in viol if v]
    rows = []
    for w in wids:
        tp = os.path.join(run_dir, "r1_%d" % w, "transcript.json")
        t = load(tp)
        chunk = [usage_of(load(f)) for f in buckets[w]]
        rec = hitrate(chunk, prefix_chars=t.get("prefix_chars"))
        n_declared = int(t.get("calls") or 0)
        rec.update({"win": w, "arm": arm, "attribution": "mtime_dump_timeline",
                    "dumps_in_window": len(buckets[w]), "calls_transcript": n_declared,
                    "count_mismatch": len(buckets[w]) != n_declared,
                    "prompt_tokens_transcript": t.get("prompt_tokens"),
                    "cache_hit_transcript": t.get("cache_hit_tokens"),
                    "cache_miss_transcript": t.get("cache_miss_tokens"),
                    "rc": t.get("rc"), "stage": t.get("stage")})
        if rec["count_mismatch"]:
            rec["problems"].append("count_mismatch: dump=%d vs transcript.calls=%d (自报低估; 以 dump 为准)"
                                   % (len(buckets[w]), n_declared))
        x = (rec["sum_hit_tok"] == t.get("cache_hit_tokens")) and (rec["sum_miss_tok"] == t.get("cache_miss_tokens"))
        rec["xref_dump_vs_transcript"] = bool(x)
        rec["status"] = "ok" if rec["calls_reported"] else "no_usage"
        rows.append(rec)
    return {"arm": arm, "dumps_dir": dumps_dir, "dumps_n": len(files),
            "attribution": "mtime_dump_timeline", "unassigned_dumps": unassigned,
            "sum_transcript_calls": sum(int(load(os.path.join(run_dir, "r1_%d" % w, "transcript.json")).get("calls") or 0)
                                        for w in wids),
            "identity_violations": [{"file": f, "detail": v} for f, v in viol], "rows": rows}


def selftest():
    """三态自检: 正常 / 恒等式违反(必须报) / 未上报(哨兵+剔除)。"""
    ok = [{"_reported": True, "prompt_tokens": 8233, "prompt_cache_hit_tokens": 128,
           "prompt_cache_miss_tokens": 8105, "completion_tokens": 1},
          {"_reported": True, "prompt_tokens": 8537, "prompt_cache_hit_tokens": 7936,
           "prompt_cache_miss_tokens": 601, "completion_tokens": 1}]
    good = hitrate(ok, prefix_chars=15119)
    bad = [dict(u) for u in ok]
    bad[1]["prompt_tokens"] = 6                                        # 总量 < 分量之和 ⇒ 口径错特征值
    v = identity_violation(bad[1])
    un = [{"_reported": False, "prompt_tokens": None, "prompt_cache_hit_tokens": None,
           "prompt_cache_miss_tokens": None, "completion_tokens": None}]
    ur = hitrate(un)
    checks = {
        "A_normal_v_all": {"got": good["v_all"], "expect": round(1 - 8706 / 16770, 4),
                           "pass": abs(good["v_all"] - round(1 - 8706 / 16770, 4)) < 1e-9},
        "A_normal_v_incr": {"got": good["v_incr"], "expect": round(1 - 601 / 8537, 4),
                            "pass": abs(good["v_incr"] - round(1 - 601 / 8537, 4)) < 1e-9},
        "B_identity_violation_detected": {"detail": v, "pass": v is not None and v["delta"] != 0},
        "C_unreported_sentinel": {"got": ur["v_all"], "unreported": ur["unreported"],
                                  "pass": ur["v_all"] == -1.0 and ur["unreported"] == 1},
        "C_unreported_problem_listed": {"problems": ur["problems"], "pass": "no_reported_usage" in ur["problems"]},
    }
    print(json.dumps(checks, ensure_ascii=False, indent=1))
    return 0 if all(v["pass"] for v in checks.values()) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dumps")
    ap.add_argument("--run-dir")
    ap.add_argument("--arm", default="?")
    ap.add_argument("--windows", type=int, default=3)
    ap.add_argument("--wins", default="", help="显式窗号列(逗号分隔), 例 7,8,9; 缺省=1..--windows (R550 行为逐位同)")
    ap.add_argument("--json")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not (a.dumps and a.run_dir):
        print("[致命] 需要 --dumps 与 --run-dir ⇒ rc=3")
        return 3
    if not os.path.isdir(a.dumps):
        print("[致命] dump 目录缺失 %s ⇒ rc=3" % a.dumps)
        return 3
    wl = [int(x) for x in a.wins.split(",") if x.strip()] or None
    out = run(a.dumps, a.run_dir, a.arm, a.windows, wins=wl)
    print("%-4s %-9s %-7s %-9s %-9s %-13s %-8s %-7s %s" % ("窗", "判分/rc", "调用", "v_all", "v_incr",
                                                           "v_prefix_chars", "未上报", "交叉校验", "阶段"))
    for r in out["rows"]:
        if r.get("status") == "missing_transcript":
            print("%-4s (缺 transcript)" % r["win"])
            continue
        print("%-4s %-9s %-7s %-9s %-9s %-13s %-8s %-7s %s" % (
            r["win"], "rc=%s" % r["rc"], r["calls"], "%.1f%%" % (100 * r["v_all"]),
            "%.1f%%" % (100 * r["v_incr"]), "%.1f%%*" % (100 * r["v_prefix_chars"]),
            r["unreported"], r["xref_dump_vs_transcript"], r.get("stage")))
    print("* v_prefix_chars 分母为**字符**(prefix_chars)而非 token ⇒ unit_mismatch, 只作口径错示例, 不作读数")
    if a.json:
        with io.open(a.json, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    if out["identity_violations"]:
        print("IDENTITY_VIOLATION %s ⇒ 器具缺陷 rc=2 (禁计入被测读数)" % json.dumps(out["identity_violations"], ensure_ascii=False))
        return 2
    if any(r.get("status") != "ok" for r in out["rows"]):
        print("SOME_WINDOW_UNJUDGEABLE ⇒ rc=1 (未上报/缺件已单列)")
        return 1
    print("ALL_WINDOWS_JUDGEABLE ⇒ rc=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
