#!/usr/bin/env python3
"""R434 结算 — P 族真假判别网格 (残余带: 真诉求 vs 假认可)。

外部真值两条 (不信被测量代码自报):
  (1) 桩侧 calls jsonl —— 逐请求落盘 (seq, ts, prompt/completion_tokens_est, messages);
  (2) 逐轮 turns jsonl —— t_start/t_end (顺序分区) + reply 原文 (回复来源判定)。

通道分离 (R432/R415 铁律: 判据必须锚定待判输入段):
  G 主答通道 = 普通对话调用      → 按「messages 末条 user 文本」内容锚定到轮 (兜底顺序分区)
  J 关系判官 = system=="只输出一个字母。" → 按 prompt 里 `用户: <text>` 内容锚定到轮
门判 domain 用 G 通道 (门只决定要不要花主答调用); J 为固定开销, 单列。

门行为外部化: reply 来源 = Skip(本地短确认模板) / Pass(远端应答) / 被 ask 消费 (非门所致, 剔除分母)。
"""
import glob
import json
import os
import sys

calls, arm, d, host, sha, grid, sfx, rundir = sys.argv[1:9]


def _i(v, dflt=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return dflt


G = json.load(open(os.path.join(d, "grid", f"task-{grid}.json"), encoding="utf-8"))
EXP = {int(e["turn"]): e for e in G.get("expected", [])}
T = json.load(open(os.path.join(d, f"turns-{arm}-{grid}{sfx}.jsonl"), encoding="utf-8"))["turns"]
rows = [json.loads(l) for l in open(calls, encoding="utf-8") if l.strip()] if os.path.exists(calls) else []

LOCAL_ACK = "收到，继续按当前方向推进"
ASK_MARK = ("续跑计划", "没有落地", "等你回答")
J_SYS = "只输出一个字母"


def _txt(call):
    msgs = call.get("messages") or []
    return [str(m.get("content") or "") for m in msgs]


def _is_j(call):
    t = _txt(call)
    return any(J_SYS in s[:40] for s in t) or any("判定用户消息相对上一轮回答" in s for s in t)


def _j_anchor(call):
    for s in _txt(call):
        if "用户:" in s or "用户：" in s:
            tail = s.split("用户:")[-1].split("用户：")[-1]
            return tail.split("\n")[0].strip()
    return None


def _g_anchor(call):
    us = [s for m, s in zip(call.get("messages") or [], _txt(call)) if str(m.get("role")) == "user"]
    return us[-1].strip() if us else None


# 文本 → 轮号 (同一文本多轮时取最近一次出现的)
def _match(text, before_ts=None):
    if not text:
        return None
    cands = [t for t in T if str(t.get("text") or "").strip() == text]
    if not cands:
        return None
    if before_ts is not None:
        c2 = [t for t in cands if float(t.get("t_start") or 0) <= before_ts + 3.0]
        if c2:
            cands = c2
    return int(cands[-1]["turn"])


starts = [float(t.get("t_start") or 0) for t in T]
by_turn = {int(t["turn"]): {"G": [], "J": [], "unassigned": []} for t in T}
assigned = set()
for j, r in enumerate(rows):
    ts = float(r.get("ts") or 0)
    turn = _match(_j_anchor(r), ts) if _is_j(r) else _match(_g_anchor(r), ts)
    if turn is None:  # 兜底: 顺序分区
        for i, t in enumerate(T):
            lo = starts[i]
            hi = starts[i + 1] if i + 1 < len(starts) else float(t.get("t_end") or lo) + 5.0
            if lo <= ts < hi:
                turn = int(t["turn"])
                break
    ch = "J" if _is_j(r) else "G"
    if turn is None:
        by_turn[T[0]["turn"]]["unassigned"].append(j)
    else:
        by_turn[turn][ch].append(j)
        assigned.add(j)

per = []
for i, t in enumerate(T):
    n = int(t["turn"])
    e = EXP.get(n, {})
    rep = str(t.get("reply") or "")
    gs, js = by_turn[n]["G"], by_turn[n]["J"]
    tok = lambda idx: sum(_i(rows[k].get("prompt_tokens_est")) + _i(rows[k].get("completion_tokens_est")) for k in idx)
    consumed = any(m in rep for m in ASK_MARK)
    if consumed:
        derived = "consumed"
    elif LOCAL_ACK in rep:
        derived = "skip"
    else:
        derived = "pass"
    per.append({"turn": n, "family": e.get("family"), "want": e.get("want"), "mech": bool(e.get("mech")),
                "G_calls": len(gs), "G_tokens": tok(gs), "J_calls": len(js), "J_tokens": tok(js),
                "actual": "skip" if derived == "skip" else ("pass" if derived == "pass" else "consumed"),
                "reply_source": derived, "consumed_as_ask_answer": consumed,
                "hit": (e.get("want") == derived) if e.get("want") and not consumed else None,
                "reply_len": len(rep), "reply_head": rep[:60], "secs": t.get("secs"),
                "t_start": t.get("t_start"), "t_end": t.get("t_end"),
                "window": [round(starts[i] - starts[0], 3),
                           round((starts[i + 1] if i + 1 < len(starts) else float(t.get("t_end") or 0) + 5.0) - starts[0], 3)]})

elig = [q for q in per if q["want"] and not q["consumed_as_ask_answer"]]
# C2 假阴性 (硬线): 真诉求轮被门跳 ⇒ 用户拿到空话。取两通道一致的证据: 门行为=skip ∨ G 调用=0
fn = [q["turn"] for q in elig if q["want"] == "pass" and q["actual"] == "skip"]
fn_calls = [q["turn"] for q in elig if q["want"] == "pass" and q["G_calls"] == 0]
fp = [q["turn"] for q in elig if q["want"] == "skip" and q["actual"] == "pass"]
fp_calls = [q["turn"] for q in elig if q["want"] == "skip" and q["G_calls"] > 0]
acc = (1.0 - (len(fn) + len(fp)) / len(elig)) if elig else None

G_rows = [k for k in assigned if not _is_j(rows[k])]
J_rows = [k for k in assigned if _is_j(rows[k])]
tot_G = sum(_i(rows[k].get("prompt_tokens_est")) + _i(rows[k].get("completion_tokens_est")) for k in G_rows)
tot_J = sum(_i(rows[k].get("prompt_tokens_est")) + _i(rows[k].get("completion_tokens_est")) for k in J_rows)
tot_calls, tot_tok = len(rows), tot_G + tot_J
unassigned = len(rows) - len(assigned)

recs = []
for f in sorted(glob.glob(os.path.join(rundir, "data/telemetry/*.jsonl"))):
    for l in open(f, encoding="utf-8-sig", errors="replace"):
        if '"local_turn_gate"' in l and "local_turn_gate_config" not in l:
            try:
                g = json.loads(l)
            except Exception:
                continue
            kv = g.get("kv") or {}
            recs.append({"decided": kv.get("decided"), "verdict": kv.get("verdict"), "basis": kv.get("basis", ""),
                         "cache_n": _i(kv.get("cache_n")), "growth_chars": _i(kv.get("growth_chars"), None),
                         "gate_prompt_len": _i(kv.get("gate_prompt_len")), "role_seed_chars": _i(kv.get("role_seed_chars")),
                         "error": kv.get("error", "")})
r1 = [r for r in recs if not str(r["basis"]).startswith("mechanical")]
out = {"arm": arm, "grid": grid, "ns": sfx, "host": host, "bin_sha": sha,
       "calls_total": tot_calls, "tokens_total": tot_tok,
       "G_calls": len(G_rows), "G_tokens": tot_G, "J_calls": len(J_rows), "J_tokens": tot_J,
       "unassigned_calls": unassigned, "attribution": "content_anchor+seq_partition[R415/R425]",
       "attribution_ok": unassigned == 0,
       "false_negative": fn, "false_negative_by_calls": fn_calls, "false_positive": fp, "false_positive_by_calls": fp_calls,
       "fn_n": len(fn), "fp_n": len(fp), "accuracy": acc,
       "measured_turns": [q["turn"] for q in elig], "measured_n": len(elig),
       "consumed_as_ask_answer": [q["turn"] for q in per if q["consumed_as_ask_answer"]],
       "per_turn": per, "gate_records": recs, "r1_records": r1,
       "gate_r1_n": len(r1), "gate_mech_n": len(recs) - len(r1),
       "r1_skips": len([r for r in r1 if r["verdict"] == "Skip"]), "r1_passes": len([r for r in r1 if r["verdict"] == "Pass"]),
       "growth_chars_seen": sorted({r["growth_chars"] for r in r1 if r["growth_chars"] is not None})}
vp = os.path.join(d, f"verdict-{arm}-{grid}{sfx}.json")
json.dump(out, open(vp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"[settle {arm}{sfx}] calls={tot_calls}(G={len(G_rows)}/J={len(J_rows)}) tok={tot_tok}(G={tot_G}/J={tot_J}) "
      f"unassigned={unassigned} FN={fn} FP={fp} acc={acc} meas={len(elig)} consumed={out['consumed_as_ask_answer']} "
      f"gate:r1={len(r1)}/mech={len(recs) - len(r1)} growth={out['growth_chars_seen']}")
for q in per:
    print(f"  t{q['turn']} {str(q['family']):<9} want={str(q['want']):<4} actual={q['actual']:<8} G={q['G_calls']} "
          f"J={q['J_calls']} tok={q['G_tokens']:>6}+{q['J_tokens']:<4} secs={q['secs']} {q['reply_head'][:26]!r}")
print("[verdict]", vp)
