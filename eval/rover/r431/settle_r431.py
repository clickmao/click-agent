#!/usr/bin/env python3
"""R431 结算 —— 复用 R430 口径 + 新增「role 额外数据挂载形状」机检。

外部真值两条: (1) 桩侧 calls jsonl (远端调用/token, 不信任被测量代码自报);
             (2) 产品遥测 local_turn_gate (判定序列/cache_n/pinned + R430 指纹)。
对齐: 网格 JSON 预注册 r1_positions (哪些轮会问到 r1) ⇒ 遥测 r1 子序列按下标对位;
     条数不符 = alignment_ok=False (fail-closed, 绝不硬对)。
用法: settle_r431.py <calls.jsonl> <arm> <dir> <host> <sha> <grid> <sfx> <rundir>
"""
import json, os, sys, glob

def _i(v):
    """遥测一律以字符串落盘 ⇒ 取值必须显式转型 (避免 '70' 与 70 的比较陷阱)。"""
    try: return int(v)
    except (TypeError, ValueError): return None

calls, arm, d, host, sha, grid, sfx, rundir = sys.argv[1:9]
gpath = os.path.join(d, "grid", f"task-{grid}.json")
G = json.load(open(gpath, encoding="utf-8"))
rows = [json.loads(l) for l in open(calls, encoding="utf-8") if l.strip()] if os.path.exists(calls) else []
pt = sum(r.get("prompt_tokens_est", 0) for r in rows)
ct = sum(r.get("completion_tokens_est", 0) for r in rows)
tel = sorted(glob.glob(os.path.join(rundir, "data/telemetry/*.jsonl")))
allg = []
for f in tel:
    for l in open(f, encoding="utf-8-sig", errors="replace"):
        if '"local_turn_gate"' in l and "local_turn_gate_config" not in l:
            try: allg.append(json.loads(l))
            except Exception: pass
recs = []
for g in allg:
    kv = g.get("kv") or {}
    recs.append({"decided": kv.get("decided"), "verdict": kv.get("verdict"), "basis": kv.get("basis", ""),
                 "cache_n": kv.get("cache_n"), "pinned": kv.get("pinned"),
                 "raw_len": kv.get("raw_len"), "error": kv.get("error", ""),
                 "prompt_sha": kv.get("prompt_sha"), "request_sha": kv.get("request_sha"),
                 "req_fields": kv.get("req_fields"), "role_seed_sha": kv.get("role_seed_sha"),
                 # R431: 挂载形状 (取自实发 prompt) 一 record 一条, 直读不推断
                 "gate_prompt_len": _i(kv.get("gate_prompt_len")), "role_seed_chars": _i(kv.get("role_seed_chars")),
                 "growth_chars": _i(kv.get("growth_chars")), "growth_lines": _i(kv.get("growth_lines"))})
mech = [r for r in recs if (r["basis"] or "").startswith("mechanical")]
r1 = [r for r in recs if not (r["basis"] or "").startswith("mechanical")]

# 归因 (R425 教训: 顺序分区 —— 不得按并列名字硬对):
#   只有真正花掉一次 LLM 往返的轮才会问 r1 门 (其余轮走"参数槽/计划续跑"路径, 秒级完成)。
#   两条独立真值交叉校验: (a) turns 文件 secs 与回复文本; (b) 门判结果与回复形态的一致性
#   —— Pass ⇒ 本轮回复是远端桩文本; Skip ⇒ 本轮回复是本地模板串。
tpath = os.path.join(d, f"turns-{arm}-{grid}{sfx}.jsonl")
T = json.load(open(tpath, encoding="utf-8"))["turns"] if os.path.exists(tpath) else []
STUB_MARK = "桩应答"
LOCAL_MARK = "收到，继续按当前方向推进"
gated = [t for t in T if float(t.get("secs", 0)) >= 5.0]
pos = [int(t["turn"]) for t in gated]
fam = [("ack" if "按这个来" in str(t.get("text", "")) else
        ("new" if "向量" in str(t.get("text", "")) else "?")) for t in gated]
align = (len(r1) == len(gated)) and len(gated) > 0
seq = []
for i, r in enumerate(r1):
    exp = None
    if i < len(gated):
        reply = str(gated[i].get("reply", ""))
        exp = ("stub" if STUB_MARK in reply else ("local_template" if LOCAL_MARK in reply else "other"))
    v = (r["verdict"] if r["decided"] == "true" else "UNDECIDED:" + (r["error"] or ""))
    ok_reply = (exp is None) or ((v == "Pass") == (exp == "stub"))
    seq.append({"pos": pos[i] if i < len(pos) else None,
                "family": fam[i] if i < len(fam) else "?",
                "msg": str(gated[i].get("text", "?")) if i < len(gated) else "?",
                "decided": r["decided"], "verdict": r["verdict"],
                "decision": v,
                "reply_shape": exp, "verdict_matches_reply": ok_reply,
                "basis": (r["basis"] or "")[:32], "cache_n": r["cache_n"], "pinned": r["pinned"], "raw_len": r["raw_len"],
                "prompt_sha": r["prompt_sha"], "request_sha": r["request_sha"],
                "req_fields": (r["req_fields"] or "")[:96], "role_seed_sha": r["role_seed_sha"],
                "gate_prompt_len": r["gate_prompt_len"], "role_seed_chars": r["role_seed_chars"],
                "growth_chars": r["growth_chars"], "growth_lines": r["growth_lines"]})
decs = [s["decision"] for s in seq]
byfam = {}
for s in seq:
    byfam.setdefault(s["family"], []).append(s["decision"])
out = {"arm": arm, "grid": grid, "ns": sfx.lstrip("-") or "b1", "binary": host, "binary_sha256": sha,
       "binary_bytes": os.path.getsize(host),
       "remote_calls": len(rows), "prompt_tokens_est": pt, "completion_tokens_est": ct, "total_tokens_est": pt + ct,
       "gate_records_all": len(recs), "gate_mechanical": len(mech), "gate_r1": len(r1),
       "alignment_ok": align, "attribution_ok": all(x["verdict_matches_reply"] for x in seq),
       "gated_positions": pos, "sequence": seq, "decisions": decs,
       "decisions_identical": (len(set(decs)) == 1 and len(decs) > 0),
       "undecided": sum(1 for x in decs if x.startswith("UNDECIDED")),
       "cache_n_seq": [s["cache_n"] for s in seq], "pinned_seq": [s["pinned"] for s in seq],
       "raw_len_seq": [s["raw_len"] for s in seq],
       "raw_len_values": sorted({str(s["raw_len"]) for s in seq if s["raw_len"]}),
       "raw_len_identical": len({str(s["raw_len"]) for s in seq if s["raw_len"]}) <= 1,
       "family_decisions": byfam,
       "prompt_sha_seq": [s["prompt_sha"] for s in seq],
       "request_sha_seq": [s["request_sha"] for s in seq],
       "role_seed_sha_seq": [s["role_seed_sha"] for s in seq],
       "req_fields_seq": [s["req_fields"] for s in seq],
       "prompt_sha_values": sorted({str(s["prompt_sha"]) for s in seq if s["prompt_sha"]}),
       "request_sha_values": sorted({str(s["request_sha"]) for s in seq if s["request_sha"]}),
       "prompt_sha_identical": len({str(s["prompt_sha"]) for s in seq if s["prompt_sha"]}) <= 1 and any(s["prompt_sha"] for s in seq),
       "request_sha_identical": len({str(s["request_sha"]) for s in seq if s["request_sha"]}) <= 1 and any(s["request_sha"] for s in seq),
       # R430 决定性判据: 输入逐位相同 ∧ 文本仍不同 ⇒ 残余在引擎侧; 否则看 req_fields/role_seed_sha 定位输入侧
       "inputs_identical": (len({str(s["prompt_sha"]) for s in seq if s["prompt_sha"]}) <= 1 and any(s["prompt_sha"] for s in seq)
                            and len({str(s["request_sha"]) for s in seq if s["request_sha"]}) <= 1 and any(s["request_sha"] for s in seq)),
       "engine_nondeterministic": bool(any(s["prompt_sha"] for s in seq)
                            and len({str(s["prompt_sha"]) for s in seq if s["prompt_sha"]}) <= 1
                            and len({str(s["request_sha"]) for s in seq if s["request_sha"]}) <= 1
                            and len({str(s["raw_len"]) for s in seq if s["raw_len"]}) > 1),
       "family_identical": {k: len(set(v)) == 1 for k, v in byfam.items()},
       "families_distinct": len({v[0] for v in byfam.values() if v}) > 1 if len(byfam) > 1 else None,
       # ---- R431 新增: 挂载形状机检 (不以「代码里有这行」为证, 只认实发 prompt 的读数) ----
       "growth_chars_seq": [s["growth_chars"] for s in seq],
       "growth_lines_seq": [s["growth_lines"] for s in seq],
       "gate_prompt_len_seq": [s["gate_prompt_len"] for s in seq],
       "role_seed_chars_seq": [s["role_seed_chars"] for s in seq],
       "growth_mounted": all((s["growth_chars"] or 0) > 0 for s in seq) and len(seq) > 0,
       "growth_absent": all((s["growth_chars"] or 0) == 0 for s in seq) and len(seq) > 0,
       # P5: 挂载后门判仍闭合 ⇒ decided 全 true 且无 thinking_truncated/UNDECIDED
       "gate_closed_all": all(s["decided"] == "true" for s in seq) and len(seq) > 0,
       "no_truncation_marker": all("truncat" not in (s.get("error") or s.get("decision") or "") for s in seq)}
p = os.path.join(d, f"verdict-{arm}-{grid}{sfx}.json")
json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("[settle]", json.dumps({k: out[k] for k in ("arm","grid","alignment_ok","attribution_ok","gated_positions","gate_r1","decisions","decisions_identical","undecided","raw_len_seq","remote_calls","total_tokens_est","cache_n_seq","pinned_seq","family_identical","families_distinct","growth_chars_seq","growth_lines_seq","gate_prompt_len_seq","growth_mounted","growth_absent","gate_closed_all","no_truncation_marker")}, ensure_ascii=False))
