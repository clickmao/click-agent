#!/usr/bin/env python3
"""R432 结算 —— 门判别力成对判据 (残余带内 r1 是否仍有判别力 + 同文逐位可复现)。

外部真值三条 (不信任被测量代码自报):
  (1) 桩侧 calls jsonl —— 远端调用次数/时间戳/token;
  (2) 产品遥测 local_turn_gate —— 判定序列/basis/指纹/cache_n (含 ts);
  (3) 驱动器 turns jsonl —— 每轮 t_start/t_end 与回复文本。
对齐: 按 **时间窗** (gate.ts 落在 [t_start,t_end] 内) 唯一命中 ⇒ 不用位置启发式
      (R430 教训: len(gate)!=len(turns), 位置对齐会静默错配)。命中不唯一/未命中 ⇒ fail-closed。
用法: settle_r432.py <calls.jsonl> <arm> <dir> <host> <sha> <grid> <sfx> <rundir>
"""
import json, os, sys, glob, datetime, hashlib
calls, arm, d, host, sha, grid, sfx, rundir = sys.argv[1:9]
G = json.load(open(os.path.join(d, "grid", f"task-{grid}.json"), encoding="utf-8"))
fam_of = {i + 1: f for i, f in enumerate(G.get("family", []))}
rows = [json.loads(l) for l in open(calls, encoding="utf-8") if l.strip()] if os.path.exists(calls) else []
pt = sum(r.get("prompt_tokens_est", 0) for r in rows)
ct = sum(r.get("completion_tokens_est", 0) for r in rows)
call_ts = sorted(float(r["ts"]) for r in rows if "ts" in r)
T = json.load(open(os.path.join(d, f"turns-{arm}-{grid}{sfx}.jsonl"), encoding="utf-8"))["turns"]


def ep(s):
    s = str(s).replace("Z", "+00:00")
    return datetime.datetime.fromisoformat(s).timestamp()


gate = []
for f in sorted(glob.glob(os.path.join(rundir, "data/telemetry/*.jsonl"))):
    for line in open(f, encoding="utf-8-sig", errors="replace"):
        if '"local_turn_gate"' in line and "local_turn_gate_config" not in line:
            try:
                g = json.loads(line)
            except Exception:
                continue
            gate.append((ep(g["ts"]), g.get("kv") or {}))

seq, unmatched, multi = [], [], []
for ts, kv in gate:
    hits = [t for t in T if float(t["t_start"]) <= ts <= float(t["t_end"])]
    if len(hits) != 1:
        (multi if hits else unmatched).append(round(ts, 3))
        rec = None
    else:
        rec = hits[0]
    pos = int(rec["turn"]) if rec else None
    reply = str(rec.get("reply") or "") if rec else ""
    win = [c for c in call_ts if rec and float(rec["t_start"]) <= c <= float(rec["t_end"])]
    basis = kv.get("basis", "") or ""
    branch = "mechanical" if basis.startswith("mechanical") else ("r1" if kv.get("decided") == "true" else "undecided")
    rawp = kv.get("raw", "") or ""
    v = kv.get("verdict") if kv.get("decided") == "true" else "UNDECIDED:" + (kv.get("error") or "")
    seq.append({"pos": pos, "family": fam_of.get(pos, "?"), "msg": str(rec.get("text", "?")) if rec else "?",
                "branch": branch, "decided": kv.get("decided"), "verdict": kv.get("verdict"), "decision": v,
                "basis": basis[:40], "raw_len": kv.get("raw_len"), "raw_prefix_sha16": hashlib.sha256(rawp.encode("utf-8")).hexdigest()[:16],
                "cache_n": kv.get("cache_n"), "pinned": kv.get("pinned"),
                "prompt_sha": kv.get("prompt_sha"), "request_sha": kv.get("request_sha"),
                "remote_calls_in_window": len(win),
                "reply_shape": ("isolated" if reply.startswith("[隔离任务]") else
                                ("stub" if "桩应答" in reply else ("local" if "收到，继续按当前方向推进" in reply else "other"))),
                })
r1 = [s for s in seq if s["branch"] == "r1"]
mech = [s for s in seq if s["branch"] == "mechanical"]
decs = [s["decision"] for s in r1]
gated_pos = sorted({s["pos"] for s in seq if s["pos"]})
all_pos = list(range(1, len(T) + 1))
ungated = [p for p in all_pos if p not in gated_pos]


def same(fam, key):
    vals = [s[key] for s in r1 if s["family"] == fam]
    return len({str(v) for v in vals}) <= 1 and len(vals) >= 2


out = {"arm": arm, "grid": grid, "ns": sfx.lstrip("-") or "b1", "binary": host, "binary_sha256": sha,
       "binary_bytes": os.path.getsize(host),
       "remote_calls": len(rows), "prompt_tokens_est": pt, "completion_tokens_est": ct, "total_tokens_est": pt + ct,
       "gate_records_all": len(seq), "gate_r1": len(r1), "gate_mechanical": len(mech),
       "alignment_ok": (len(unmatched) == 0 and len(multi) == 0 and len(seq) > 0),
       "alignment_unmatched": unmatched, "alignment_ambiguous": multi,
       "attribution_ok": all((s["decision"] == "Pass") == (s["remote_calls_in_window"] >= 1) for s in seq if s["pos"]),
       "isolation_hits": [s["pos"] for s in seq if s["reply_shape"] == "isolated"],
       "gated_positions": gated_pos, "ungated_positions": ungated,
       "sequence": seq,
       "r1_decisions": decs, "r1_decisions_identical": (len(set(decs)) == 1 and len(decs) > 0),
       "r1_has_pass": ("Pass" in decs), "r1_has_skip": ("Skip" in decs),
       "undecided": sum(1 for x in decs if str(x).startswith("UNDECIDED")),
       "C1_r1_discriminates": ("Pass" in decs and "Skip" in decs),
       "C1p_pair_discriminates": (any(s["decision"] == "Pass" for s in mech) and "Skip" in decs),
       "C2_ack_repeat_stable": (same("ack", "decision") and same("ack", "raw_len") and same("ack", "raw_prefix_sha16") and same("ack", "prompt_sha")),
       "C2_cont_repeat_stable": (same("cont", "decision") and same("cont", "raw_len") and same("cont", "raw_prefix_sha16") and same("cont", "prompt_sha")),
       "C2_details": {f: {"decisions": [s["decision"] for s in r1 if s["family"] == f],
                          "raw_len": [s["raw_len"] for s in r1 if s["family"] == f],
                          "raw_prefix_sha16": [s["raw_prefix_sha16"] for s in r1 if s["family"] == f],
                          "prompt_sha": sorted({str(s["prompt_sha"]) for s in r1 if s["family"] == f})}
                      for f in ("ack", "cont", "adversarial_correct", "adversarial_park")},
       "C3_alignment_and_attribution": None,  # 下面回填
       "C4_no_isolation": True, "C5_mechanical_control_ok": None,
       "cache_n_seq": [s["cache_n"] for s in r1], "pinned_seq": [s["pinned"] for s in r1],
       "raw_len_seq": [s["raw_len"] for s in r1],
       "family_decisions": {f: [s["decision"] for s in r1 if s["family"] == f] for f in
                            sorted({s["family"] for s in r1})}}
out["C3_alignment_and_attribution"] = bool(out["alignment_ok"] and out["attribution_ok"])
out["C4_no_isolation"] = len(out["isolation_hits"]) == 0
mc = [s for s in seq if s["family"] == "mechanical_control"]
out["C5_mechanical_control_ok"] = bool(mc and all(s["branch"] == "mechanical" for s in mc)
                                       and not any(s["family"] == "mechanical_control" for s in r1))
rule = ("PASS = C1 and C2ack and C2cont and C3 and C4 and C5; "
        "PARTIAL = (not C1) and C1p and C2ack and C2cont and C3 and C4 and C5; "
        "FAIL = (not C3) or (not C4) or (not C5); UNDECIDED = no r1 reading")
out["verdict_rule"] = rule
if out["gate_r1"] == 0:
    out["verdict"] = "UNDECIDED"
elif not (out["C3_alignment_and_attribution"] and out["C4_no_isolation"] and out["C5_mechanical_control_ok"]):
    out["verdict"] = "FAIL"
elif out["C1_r1_discriminates"] and out["C2_ack_repeat_stable"] and out["C2_cont_repeat_stable"]:
    out["verdict"] = "PASS"
elif out["C1p_pair_discriminates"] and out["C2_ack_repeat_stable"] and out["C2_cont_repeat_stable"]:
    out["verdict"] = "PARTIAL"
else:
    out["verdict"] = "FAIL"
print("[verdict]", out["verdict"], "|", rule)
p = os.path.join(d, f"verdict-{arm}-{grid}{sfx}.json")
json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("[settle]", json.dumps({k: out[k] for k in ("arm", "grid", "verdict", "gate_records_all", "gate_r1", "gate_mechanical",
      "alignment_ok", "attribution_ok", "gated_positions", "ungated_positions", "isolation_hits", "r1_decisions",
      "C1_r1_discriminates", "C1p_pair_discriminates", "C2_ack_repeat_stable", "C2_cont_repeat_stable",
      "C5_mechanical_control_ok", "remote_calls", "total_tokens_est", "raw_len_seq")}, ensure_ascii=False))
