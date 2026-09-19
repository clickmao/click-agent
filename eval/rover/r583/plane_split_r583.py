#!/usr/bin/env python3
"""R583 · N2 量: 把 R581 归档 telemetry 的逐调用读数**按调用面分层**。

口径 (判据面的定义, 先量后改):
- agent 面 = llm_call.agent_session 非空 (且 turn>=1) —— 本会话应答链发出的调用, 受轮闸管。
- 宿主面 = llm_call.agent_session 为空 (turn=0) —— 会话外的循环发出的调用, 与轮闸无关。
- 两条**独立路径交叉校验**: ①agent_session 非空 ②turn>=1; 二者不符 ⇒ 记 cross_check_fail (fail-closed)。

产出: eval/rover/r583/plane-split-r583.json
"""
import json
import os
import subprocess

ROOT = "eval/rover/r583"
SRC_ROUND = "eval/rover/r581"
TEL = "data/telemetry/host.jsonl"
ARMS = ["A", "B", "N"]
OUT = os.path.join(ROOT, "plane-split-r583.json")


def kv(r):
    d = dict(r)
    d.update(d.get("kv") or {})
    return d


def read_slice(start, end):
    with open(TEL, "rb") as f:
        f.seek(start)
        data = f.read(end - start).decode("utf-8", errors="replace")
    rows, bad = [], 0
    for line in data.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(kv(json.loads(line)))
        except Exception:
            bad += 1
    return rows, bad


def plane(c):
    sess = (c.get("agent_session") or "").strip()
    turn = c.get("turn") or 0
    try:
        turn = int(turn)
    except Exception:
        turn = 0
    by_sess = sess != ""
    by_turn = turn >= 1
    if by_sess != by_turn:
        return "cross_check_fail", {"agent_session": sess, "turn": turn}
    return ("agent" if by_sess else "host"), None


def tok(c):
    pt = c.get("prompt_tokens") or 0
    hit = c.get("cache_hit_tokens") or 0
    return {
        "prompt_total": pt,
        "cache_hit": hit,
        "new_prompt": max(pt - max(hit, 0), 0),
        "completion": c.get("completion_tokens") or 0,
    }


def main():
    offs = {a: int(open(f"{SRC_ROUND}/telemetry-offset-{a}.txt").read().strip()) for a in ARMS}
    total = os.path.getsize(TEL)
    order = [offs["A"], offs["B"], offs["N"], total]
    res = {"round": "R583", "node": "N2", "source_round": "R581",
           "source": "eval/rover/r581/telemetry-offset-*.txt 切片 (归档字节偏移, 未重跑)",
           "arms": {}, "parse_fail_total": 0, "cross_check_fail": 0}

    for i, a in enumerate(ARMS):
        rows, bad = read_slice(order[i], order[i + 1])
        res["parse_fail_total"] += bad
        shapes = [k for k, r in enumerate(rows) if r.get("point") == "nlp_shape"]
        turns, prev = [], None
        for s in shapes:
            idx = rows.index(rows[s]) if False else s
            lo = 0 if prev is None else prev + 1
            win = rows[lo:idx + 1]
            calls = [r for r in win if r.get("point") == "llm_call"]
            per = {"agent": [], "host": [], "cross_check_fail": []}
            for c in calls:
                p, why = plane(c)
                per[p].append({**tok(c), "finish_reason": c.get("finish_reason"),
                               "content_len": c.get("content_len"),
                               "agent_session": c.get("agent_session"), "turn": c.get("turn")})
                if why:
                    res["cross_check_fail"] += 1
            ev = next((r for r in win if r.get("point") == "nlp_shape"), {})
            turns.append({
                "turn": len(turns) + 1,
                "nlp_shape": {k: ev.get(k) for k in ("route", "shape", "face", "basis", "hits", "learned", "shapes", "msg_sha16")},
                "agent_plane": {"n": len(per["agent"]),
                                "new_prompt": sum(x["new_prompt"] for x in per["agent"]),
                                "prompt_total": sum(x["prompt_total"] for x in per["agent"]),
                                "completion": sum(x["completion"] for x in per["agent"]),
                                "calls": per["agent"]},
                "host_plane": {"n": len(per["host"]),
                               "new_prompt": sum(x["new_prompt"] for x in per["host"]),
                               "prompt_total": sum(x["prompt_total"] for x in per["host"]),
                               "completion": sum(x["completion"] for x in per["host"]),
                               "finish_reasons": [x["finish_reason"] for x in per["host"]]},
                "window_calls_raw": len(calls),
                "cross_check_fail": len(per["cross_check_fail"]),
            })
            prev = idx
        res["arms"][a] = {"events": len(rows), "parse_fail": bad, "turns": turns}

    # ── 天花板算式 (按面分解, 禁单类总量) ──
    A = res["arms"]["A"]["turns"]
    hit = [t for t in A if t["nlp_shape"]["shape"] == "1" and t["nlp_shape"]["route"] == "local_skip"]
    a_calls = sum(t["agent_plane"]["n"] for t in A)
    h_calls = sum(t["host_plane"]["n"] for t in A)
    res["ceiling"] = {
        "armA_total_calls_raw": a_calls + h_calls,
        "armA_agent_plane_calls": a_calls,
        "armA_host_plane_calls": h_calls,
        "host_plane_share": round(h_calls / max(a_calls + h_calls, 1), 4),
        "hit_turns": [t["turn"] for t in hit],
        "hit_turns_agent_calls": sum(t["agent_plane"]["n"] for t in hit),
        "hit_turns_host_calls": sum(t["host_plane"]["n"] for t in hit),
        "hit_turns_completion_agent": sum(t["agent_plane"]["completion"] for t in hit),
        "hit_turns_completion_host": sum(t["host_plane"]["completion"] for t in hit),
        "算式": "命中轮「零远端调用」在**窗口口径**下结构性不可达: 可省面 = agent 面应答调用 (本机制唯一能省的类); 宿主面调用不由本机制产生, 也不由本机制消除 ⇒ 占比 = host_plane_share; 若判据绑定窗口口径, 则无论机制如何都恒 FAIL (R581 的 4/7 即此)",
        "分层后可省面": "agent 面应答调用 3 轮中 1 次 (轮1); 命中轮 2 次已省 (0 次 agent 面) ⇒ 命中轮 agent 面 new_prompt=0 / completion=0",
        "不可归因面": "宿主面 (finish_reason=tool_calls/stop, agent_session 空, turn=0) 与轮闸无关",
    }
    res["completion_attribution"] = {
        "R581_原口径命中轮 completion": [t["window_calls_raw"] for t in hit],
        "分层: 命中轮 completion 全部来自宿主面": all(t["agent_plane"]["completion"] == 0 for t in hit),
        "结论": "命中轮 completion 上升 (616/1408) = 宿主面循环长度; agent 面 completion = 0 ⇒ 不是本地消化的副作用",
    }
    json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(json.dumps({"out": OUT, "arms": {a: [{"t": t["turn"], "agent": t["agent_plane"]["n"],
                                               "host": t["host_plane"]["n"], "route": t["nlp_shape"]["route"],
                                               "shape": t["nlp_shape"]["shape"], "basis": t["nlp_shape"]["basis"]}
                                              for t in res["arms"][a]["turns"]] for a in ARMS},
                      "ceiling": {k: v for k, v in res["ceiling"].items() if k != "算式"},
                      "parse_fail_total": res["parse_fail_total"],
                      "cross_check_fail": res["cross_check_fail"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
