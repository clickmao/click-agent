#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R512 判据机检器: 按**预注册** criteria 逐条机检取值 (禁手抄数字)。

输入: <D>/report.json (聚合读数) · eval/rover/r512/prereg-r512.json (阈值/器具哈希) ·
      eval/rover/r512/taskset-r512.json (题面 sha) · 可选 --precond-json (铁律11 前置器输出)。
输出: stdout 判定表 + <--json> 落盘 (含每窗口 逐 (臂,题) 的 calls/tokens/用例 三元组)。
口径: agent 侧 = 本侧实现体; codex 侧 = 外部真值; 比值只在本窗口内算 (跨轮禁相减)。
"""
from __future__ import annotations
import argparse, collections, io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--report", help="默认 <run-dir>/report.json")
    ap.add_argument("--prereg", default=os.path.join(HERE, "prereg-r512.json"))
    ap.add_argument("--taskset", default=os.path.join(HERE, "taskset-r512.json"))
    ap.add_argument("--precond-json")
    ap.add_argument("--json")
    a = ap.parse_args()
    rep = json.load(io.open(a.report or os.path.join(a.run_dir, "report.json"), encoding="utf-8-sig"))
    pre = json.load(io.open(a.prereg, encoding="utf-8-sig"))
    ts = json.load(io.open(a.taskset, encoding="utf-8-sig"))
    prompt_sha = {t["tid"]: t["prompt_sha256"] for t in ts["tasks"]}

    rows = rep["rows"]
    import re
    RULES = pre["criteria"]

    def thr(cid, pat, default=None):
        m = re.search(pat, RULES[cid]["rule"])
        if m:
            return float(m.group(1)), "预注册规则里的常数"
        if default is not None:
            return float(default), "规则为比较式(无常数) ⇒ 比值上界由规则式推导"
        print("[致命] 预注册 %s 规则里取不到阈值 ⇒ fail-closed (禁硬编码常数)" % cid)
        sys.exit(3)

    T_TOK, T_TOK_SRC = thr("C3_token_down", r"<=\s*([0-9.]+)\s*\*")
    T_CALL, T_CALL_SRC = thr("C4_remote_calls_down", r"<=\s*([0-9.]+)", default=1.0)
    win_of = {}
    for r in rows:
        win_of[(r.get("run") or r["arm"])] = r
    # 每 run 的窗口: A-r1/C-r1 → w1 ; A-r2/C-r2 → w2 ; 其余按尾号
    def win(run):
        import re
        m = re.search(r"-r(\d+)$", run or "")
        return "w%s" % (m.group(1) if m else "?")

    buckets = collections.defaultdict(dict)   # (win, tid) -> arm -> row
    for r in rows:
        arm = r["arm"]
        buckets[(win(r.get("run") or arm), r["tid"])][arm] = r

    checks, tables = [], {}
    models = collections.defaultdict(set)
    for r in rows:
        for m in (r.get("models") or []):
            models[r["arm"]].add(m)
    c1 = {"all_models": {k: sorted(v) for k, v in models.items()},
          "nonempty": all(models[k] for k in models),
          "equal": len({frozenset(v) for v in models.values()}) == 1,
          "prompt_sha": prompt_sha,
          "taskset_sha256": pre["instruments"]["taskset"]["sha256"]}
    checks.append({"id": "C1_same_env_same_input_same_model", "pass": bool(c1["nonempty"] and c1["equal"]), "detail": c1})

    qrow, trow, crow_ = [], [], []
    for (w, tid), byarm in sorted(buckets.items()):
        cdx = byarm.get("C")
        if not cdx:
            continue
        line = {"window": w, "tid": tid, "codex": {"cases": "%s/%s" % (cdx["cases_pass"], cdx["cases_total"]),
                                                   "calls": cdx["calls"], "tok": cdx["total_tokens"],
                                                   "elapsed_s": cdx["elapsed_s"]}}
        for arm in ("A", "B"):
            r = byarm.get(arm)
            if not r:
                continue
            line[arm] = {"cases": "%s/%s" % (r["cases_pass"], r["cases_total"]), "calls": r["calls"],
                         "tok": r["total_tokens"], "tok_ratio": round((r["total_tokens"] or 0) / cdx["total_tokens"], 4) if cdx["total_tokens"] else None,
                         "calls_ratio": round((r["calls"] or 0) / cdx["calls"], 4) if cdx["calls"] else None,
                         "quality_ge_codex": r["cases_pass"] >= cdx["cases_pass"]}
            qrow.append((r["cases_pass"] >= cdx["cases_pass"]))
            trow.append(line[arm]["tok_ratio"])
            crow_.append(line[arm]["calls_ratio"])
        tables["%s/%s" % (w, tid)] = line

    c2 = {"pairs": len(qrow), "quality_not_lower_all": bool(qrow) and all(qrow),
          "detail": {k: {"agent_cases": v.get("A", {}).get("cases") or v.get("B", {}).get("cases"),
                         "codex_cases": v["codex"]["cases"]} for k, v in tables.items()}}
    checks.append({"id": "C2_quality_not_lower", "pass": bool(c2["quality_not_lower_all"]), "detail": c2})
    mx_t = max([x for x in trow if x is not None], default=None)
    mx_c = max([x for x in crow_ if x is not None], default=None)
    checks.append({"id": "C3_token_down", "pass": bool(mx_t is not None and mx_t <= T_TOK),
                   "detail": {"ratios": trow, "max": mx_t, "threshold": T_TOK, "threshold_source": T_TOK_SRC}})
    checks.append({"id": "C4_remote_calls_down", "pass": bool(mx_c is not None and mx_c <= T_CALL),
                   "detail": {"ratios": crow_, "max": mx_c, "threshold": T_CALL, "threshold_source": T_CALL_SRC}})
    if a.precond_json and os.path.isfile(a.precond_json):
        pj = json.load(io.open(a.precond_json, encoding="utf-8-sig"))
        ok = bool(pj.get("acceptable_scoped"))
        checks.append({"id": "C5_executable_and_correct", "pass": ok,
                       "detail": {"acceptable_scoped": pj.get("acceptable_scoped"),
                                  "executable_and_correct": pj.get("executable_and_correct"),
                                  "self_report_mismatch": pj.get("self_report_mismatch"),
                                  "blocked_scoped": pj.get("blocked_scoped")}})
    else:
        checks.append({"id": "C5_executable_and_correct", "pass": False,
                       "detail": {"note": "未提供 --precond-json ⇒ 未测, 计未过 (禁以未测当通过)"}})

    out = {"run_dir": a.run_dir, "prereg": a.prereg, "checks": checks, "tables": tables,
           "prereg_prompt_sha": pre.get("prompt_sha256")}
    print("%-34s %s" % ("判据", "结果"))
    for c in checks:
        print("%-34s %s" % (c["id"], "PASS" if c["pass"] else "FAIL"))
        if c["id"] == "C3_token_down":
            print("    token 比 (agent/codex, 逐窗口逐题): %s ⇒ max=%s" % (c["detail"]["ratios"], c["detail"]["max"]))
        if c["id"] == "C4_remote_calls_down":
            print("    调用比 (agent/codex): %s ⇒ max=%s" % (c["detail"]["ratios"], c["detail"]["max"]))
    for k, v in tables.items():
        print("  %-8s codex %-6s 调用 %-4s tok %-8s | A %-6s %-4s %-8s | B %s" %
              (k, v["codex"]["cases"], v["codex"]["calls"], v["codex"]["tok"],
               v.get("A", {}).get("cases", "-"), v.get("A", {}).get("calls", "-"), v.get("A", {}).get("tok", "-"),
               json.dumps(v.get("B"), ensure_ascii=False)))
    if a.json:
        with io.open(a.json, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
        print("OUT=" + a.json)
    return 0 if all(c["pass"] for c in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
