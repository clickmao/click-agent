#!/usr/bin/env python3
"""R439 结算 — 端到端 BRJ 网格（承重 = 用户一轮 total token 降幅 ≥30%）。

外部真值两条（不信被测量自报）:
  (1) 桩侧 calls jsonl —— 逐请求落盘（seq, ts, prompt/completion_tokens_est, messages）⇒ **远端 API 请求数/token**;
  (2) 逐轮 turns jsonl —— t_start/t_end（顺序分区）+ reply 原文（回复来源判定）。

通道分离（R432/R415 铁律: 判据必须锚定待判输入段）:
  G 主答通道 = 普通对话调用            → 按「messages 末条 user 文本」内容锚定到轮（兜底顺序分区）
  J 关系判官 = system == <派生自源码>  → 按 J prompt 里 `用户: <text>` 内容锚定到轮
  标记**全部由 channel_marks.py 从源码程序化派生**（R435 教训: 禁手打, 含不可见码位风险）。

R438 新增(器具继承)（器具修, 见 docs/plans/v0.57.0-r438-e2e-brj-token-kpi.md §4）:
  * S1 复现性负控: 分类器先在 **R434 磁盘档案**上重算, 必须复现已登记的 G/J 计数（否则 fail-closed, exit 6）;
  * S2 双源交叉: 桩侧 J 远端调用数 与 产品遥测 `point=correction_judge` 的 source≠local 条数 交叉;
  * S3 本地侧披露: 判官 local_state 分布（失败原因）+ 本地生成 token + 判官耗时（**不计入 API token**）。
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from channel_marks import derive as derive_marks  # noqa: E402

MARKS = derive_marks()
J_SYS = MARKS["j_system"]
J_FIRST = MARKS["j_first_line"]
J_ANCHOR = MARKS["j_user_anchor"]

calls, arm, d, host, sha, grid, sfx, rundir = sys.argv[1:9]
d = os.path.abspath(d)
ARCHIVE = os.path.join(os.path.dirname(d), "r434")


def _i(v, dflt=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return dflt


def _in(v):
    """缺失 ⇒ None（区别于 0）—— 用于「没读到」不得记成 0 的字段。"""
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _txt(call):
    return [str(m.get("content") or "") for m in (call.get("messages") or [])]


def _is_j(call):
    t = _txt(call)
    return any(J_SYS in s[:40] for s in t) or any(J_FIRST in s for s in t)


def _j_anchor(call):
    for s in _txt(call):
        if J_ANCHOR in s:
            return s.split(J_ANCHOR)[-1].split("\n")[0].strip()
    return None


def _g_anchor(call):
    us = [s for m, s in zip(call.get("messages") or [], _txt(call)) if str(m.get("role")) == "user"]
    return us[-1].strip() if us else None


def _read_rows(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()] if os.path.exists(path) else []


# ---------- S1 复现性负控: 分类器必须在旧档案上复现已登记计数 ----------
def repro_archive():
    out = []
    for arm_tag in ("A-p8-a1", "B-p8-b1", "BRJ-p8-k1", "BP-p8-d1", "A-p12-n1", "B-p12-o1"):
        c = os.path.join(ARCHIVE, f"calls-{arm_tag}.jsonl")
        v = os.path.join(ARCHIVE, f"verdict-{arm_tag}.json")
        if not (os.path.exists(c) and os.path.exists(v)):
            out.append({"archive": arm_tag, "skip": "档案缺失"})
            continue
        rows = _read_rows(c)
        g = len([r for r in rows if not _is_j(r)])
        j = len([r for r in rows if _is_j(r)])
        rec = json.load(open(v, encoding="utf-8"))
        if "G_calls" not in rec or "J_calls" not in rec:
            out.append({"archive": arm_tag, "recomputed": [g, j], "skip": "该档案未登记 G/J 计数(旧版 verdict)"})
            continue
        exp = (rec["G_calls"], rec["J_calls"])
        out.append({"archive": arm_tag, "recomputed": [g, j], "recorded": list(exp), "match": (g, j) == exp})
    return out


# ---------- 结算 ----------
G_GRID = json.load(open(os.path.join(d, "grid", f"task-{grid}.json"), encoding="utf-8"))
EXP = {int(e["turn"]): e for e in G_GRID.get("expected", [])}
T = json.load(open(os.path.join(d, f"turns-{arm}-{grid}{sfx}.jsonl"), encoding="utf-8"))["turns"]
rows = _read_rows(calls)

LOCAL_ACK = "收到，继续按当前方向推进"
ASK_MARK = ("续跑计划", "没有落地", "等你回答")


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
    if turn is None:  # 兜底: 顺序分区（与 R434 同法, 已由 R434 读数背书）
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
    tok = lambda idx: sum(_i(rows[k].get("prompt_tokens_est")) + _i(rows[k].get("completion_tokens_est")) for k in idx)  # noqa: E731
    consumed = any(m in rep for m in ASK_MARK)
    if consumed:
        derived = "consumed"
    elif LOCAL_ACK in rep:
        derived = "skip"
    else:
        derived = "pass"
    per.append({"turn": n, "family": e.get("family"), "want": e.get("want"), "mech": bool(e.get("mech")),
                "G_calls": len(gs), "G_tokens": tok(gs), "J_calls": len(js), "J_tokens": tok(js),
                "actual": derived, "reply_source": derived, "consumed_as_ask_answer": consumed,
                "hit": (e.get("want") == derived) if e.get("want") and not consumed else None,
                "reply_len": len(rep), "reply_head": rep[:60], "secs": t.get("secs"),
                "t_start": t.get("t_start"), "t_end": t.get("t_end"),
                "window": [round(starts[i] - starts[0], 3),
                           round((starts[i + 1] if i + 1 < len(starts) else float(t.get("t_end") or 0) + 5.0) - starts[0], 3)]})

elig = [q for q in per if q["want"] and not q["consumed_as_ask_answer"]]
fn = [q["turn"] for q in elig if q["want"] == "pass" and q["actual"] == "skip"]
fn_calls = [q["turn"] for q in elig if q["want"] == "pass" and q["G_calls"] == 0]
fp = [q["turn"] for q in elig if q["want"] == "skip" and q["actual"] == "pass"]
fp_calls = [q["turn"] for q in elig if q["want"] == "skip" and q["G_calls"] > 0]
acc = (1.0 - (len(fn) + len(fp)) / len(elig)) if elig else None

G_rows = [k for k in assigned if not _is_j(rows[k])]
J_rows = [k for k in assigned if _is_j(rows[k])]
tot_G = sum(_i(rows[k].get("prompt_tokens_est")) + _i(rows[k].get("completion_tokens_est")) for k in G_rows)
tot_J = sum(_i(rows[k].get("prompt_tokens_est")) + _i(rows[k].get("completion_tokens_est")) for k in J_rows)

# ---------- 遥测: 判官来源/失败原因/本地 token ----------
recs, jtel = [], []
for f in sorted(glob.glob(os.path.join(rundir, "data/telemetry/*.jsonl"))):
    for l in open(f, encoding="utf-8-sig", errors="replace"):
        if '"local_turn_gate"' in l and "local_turn_gate_config" not in l:
            try:
                g = json.loads(l)
            except Exception:
                continue
            kv = g.get("kv") or {}
            recs.append({"decided": kv.get("decided"), "verdict": kv.get("verdict"), "basis": kv.get("basis", ""),
                         "cache_n": _i(kv.get("cache_n")), "growth_chars": _in(kv.get("growth_chars")),
                         "gate_prompt_len": _i(kv.get("gate_prompt_len")), "role_seed_chars": _i(kv.get("role_seed_chars")),
                         "error": kv.get("error", "")})
        if '"correction_judge"' in l:
            try:
                g = json.loads(l)
            except Exception:
                continue
            kv = g.get("kv") or {}
            jtel.append({"source": kv.get("source", ""), "kind": kv.get("kind", ""), "letter": kv.get("letter", ""),
                         "local_state": kv.get("local_state", ""), "prompt_len": _i(kv.get("prompt_len")),
                         "ms": _i(kv.get("ms")), "tokens": _i(kv.get("tokens")),
                         "msg_head": kv.get("msg_head", "")})
r1 = [r for r in recs if not str(r["basis"]).startswith("mechanical")]

# S2 双源交叉（定义修正, 见 §4 器具修: 真"远端判决"= 请求被真实构造 ⇒ prompt_len>0;
#      prompt_len==0 的 source!=local 属**结构性判定**(mechanic 标记/无上一轮), 未发任何请求)
j_remote_stub = len(J_rows)
j_tel_constructed = len([x for x in jtel if x["source"] != "local" and x["prompt_len"] > 0])
j_tel_structural = len([x for x in jtel if x["source"] != "local" and x["prompt_len"] == 0])
j_tel_local = len([x for x in jtel if x["source"] == "local"])

s1 = repro_archive()
s1_compared = [x for x in s1 if "match" in x]
s1_ok = len(s1_compared) >= 4 and all(x["match"] for x in s1_compared)

out = {"arm": arm, "grid": grid, "ns": sfx, "host": host, "bin_sha": sha,
       "marks": MARKS,
       "calls_total": len(rows), "tokens_total": tot_G + tot_J,
       "G_calls": len(G_rows), "G_tokens": tot_G, "J_calls": len(J_rows), "J_tokens": tot_J,
       "unassigned_calls": len(rows) - len(assigned), "attribution": "content_anchor+seq_partition[R415/R425]",
       "attribution_ok": len(rows) - len(assigned) == 0,
       "false_negative": fn, "false_negative_by_calls": fn_calls, "false_positive": fp, "false_positive_by_calls": fp_calls,
       "fn_n": len(fn), "fp_n": len(fp), "accuracy": acc,
       "measured_turns": [q["turn"] for q in elig], "measured_n": len(elig),
       "consumed_as_ask_answer": [q["turn"] for q in per if q["consumed_as_ask_answer"]],
       "per_turn": per,
       "judge_telemetry": jtel,
       "judge_source_count": {"local": j_tel_local, "non_local": j_tel_constructed, "events": len(jtel),
                              "structural_no_request": j_tel_structural},
       "judge_remote_fallback_n": len([x for x in jtel if x["source"] == "remote_fallback" and x["prompt_len"] > 0]),
       "judge_local_state": {k: len([x for x in jtel if x["local_state"].split(":")[0] == k])
                             for k in sorted({x["local_state"].split(":")[0] for x in jtel})},
       "judge_local_tokens": sum(x["tokens"] for x in jtel if x["source"] == "local"),
       "judge_local_ms": [x["ms"] for x in jtel if x["source"] == "local"],
       "cross_check_S2": {"stub_J_remote": j_remote_stub, "telemetry_remote_constructed": j_tel_constructed,
                          "telemetry_structural_no_request": j_tel_structural,
                          "delta": j_remote_stub - j_tel_constructed},
       "repro_archive_S1": s1, "repro_archive_ok": s1_ok, "repro_archive_compared": len(s1_compared),
       "gate_records": recs, "r1_records": r1,
       "gate_r1_n": len(r1), "gate_mech_n": len(recs) - len(r1),
       "r1_skips": len([r for r in r1 if r["verdict"] == "Skip"]), "r1_passes": len([r for r in r1 if r["verdict"] == "Pass"]),
       "growth_chars_seen": sorted({r["growth_chars"] for r in r1 if r["growth_chars"] is not None})}
vp = os.path.join(d, f"verdict-{arm}-{grid}{sfx}.json")
json.dump(out, open(vp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"[settle {arm}{sfx}] calls={len(rows)}(G={len(G_rows)}/J={len(J_rows)}) tok={tot_G + tot_J}(G={tot_G}/J={tot_J}) "
      f"unassigned={out['unassigned_calls']} FN={fn} FP={fp} acc={acc} meas={len(elig)} consumed={out['consumed_as_ask_answer']} "
      f"gate:r1={len(r1)}/mech={len(recs) - len(r1)}")
print(f"[settle] 判官遥测 events={len(jtel)} local={j_tel_local} 真远端={j_tel_constructed} 结构={j_tel_structural} "
      f"local_tokens={out['judge_local_tokens']} local_ms={out['judge_local_ms']} states={out['judge_local_state']} rf={out['judge_remote_fallback_n']}")
print(f"[settle] S2 双源: stub_J={j_remote_stub} vs 遥测真远端(构造过请求)={j_tel_constructed} (+结构性{j_tel_structural}")
print(f"[settle] S1 复现档案: ok={s1_ok} compared={len(s1_compared)} "
      f"{[(x.get('archive'), x.get('recomputed'), x.get('recorded') or x.get('skip')) for x in s1]}")
for q in per:
    print(f"  t{q['turn']:>2} {str(q['family']):<18} want={str(q['want']):<4} actual={q['actual']:<8} G={q['G_calls']} "
          f"J={q['J_calls']} tok={q['G_tokens']:>6}+{q['J_tokens']:<4} secs={q['secs']} {q['reply_head'][:24]!r}")
print("[verdict]", vp)
if not s1_ok:
    print("[致命] S1 复现性负控失败 ⇒ 分类器不可信, 读数作废")
    sys.exit(6)
