#!/usr/bin/env python3
"""R429 判据聚合 (预注册: docs/plans/v0.50.0-r429-decision-cache-pin.md §5)。

用法: python3 analyze_r429.py pre=<verdict.json> post=<verdict.json> [ctrl=<verdict.json>] [--ns <sfx>]
P5a = PRE 的 r1 门判序列**不恒定**(≥2 种判定 或 ≥1 未判定) ⇒ 复现「决策不可复现」
P5b = POST 的 r1 门判序列恒定 ∧ 零未判定 ⇒ 钉死后可复现
P6  = POST total_tokens_est ≤ PRE ∧ remote_calls ≤ PRE
负控 = 判别力网格: 族内恒定 ∧ 族间不同 (证仪器不是「恒 Skip」)
"""
import json, sys, pathlib
args = [a for a in sys.argv[1:] if not a.startswith("--")]
ns = "b1"
if "--ns" in sys.argv: ns = sys.argv[sys.argv.index("--ns") + 1]
d = {}
for a in args:
    k, v = a.split("=", 1); d[k] = json.load(open(v, encoding="utf-8"))
def dec(x): return [s["decision"] for s in x["sequence"]]
out = {"ns": ns}
pre, post, ctrl = d.get("pre"), d.get("post"), d.get("ctrl")
if pre:
    out["P5a_pre_reproduced"] = (not pre["decisions_identical"]) or pre["undecided"] > 0
    out["pre"] = {"arm": pre["arm"], "grid": pre["grid"], "r1": pre["gate_r1"], "undecided": pre["undecided"],
                  "decisions": dec(pre), "identical": pre["decisions_identical"], "align": pre["alignment_ok"],
                  "remote_calls": pre["remote_calls"], "total_tokens_est": pre["total_tokens_est"],
                  "cache_n_seq": pre["cache_n_seq"], "pinned_seq": pre["pinned_seq"],
                  "sha": pre["binary_sha256"][:12], "bytes": pre["binary_bytes"]}
if post:
    out["P5b_post_identical"] = bool(post["decisions_identical"] and post["undecided"] == 0)
    out["P5c_post_raw_len_identical"] = bool(post.get("raw_len_identical"))
    out["post"] = {"arm": post["arm"], "grid": post["grid"], "r1": post["gate_r1"], "undecided": post["undecided"],
                   "decisions": dec(post), "identical": post["decisions_identical"], "align": post["alignment_ok"],
                   "remote_calls": post["remote_calls"], "total_tokens_est": post["total_tokens_est"],
                   "cache_n_seq": post["cache_n_seq"], "pinned_seq": post["pinned_seq"],
                   "sha": post["binary_sha256"][:12], "bytes": post["binary_bytes"]}
if pre and post:
    out["P6_post_tokens_le_pre"] = post["total_tokens_est"] <= pre["total_tokens_est"]
    out["P6_post_calls_le_pre"] = post["remote_calls"] <= pre["remote_calls"]
    out["delta_tokens"] = post["total_tokens_est"] - pre["total_tokens_est"]
    out["delta_calls"] = post["remote_calls"] - pre["remote_calls"]
    out["binary_distinct"] = pre["binary_sha256"] != post["binary_sha256"]
if ctrl:
    out["ctrl"] = {"grid": ctrl["grid"], "decisions": dec(ctrl), "family_identical": ctrl["family_identical"],
                   "families_distinct": ctrl["families_distinct"], "identical": ctrl["decisions_identical"],
                   "undecided": ctrl["undecided"], "cache_n_seq": ctrl["cache_n_seq"], "pinned_seq": ctrl["pinned_seq"]}
    out["ctrl_pass"] = all(ctrl["family_identical"].values()) and bool(ctrl["families_distinct"])
p = pathlib.Path("/home/agentuser/AgentFramework/eval/rover/r429") / f"verdict-r429-aggregate-{ns}.json"
json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False, indent=1))
