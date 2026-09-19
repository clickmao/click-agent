#!/usr/bin/env python3
"""R581 · 读数抽取 + 判据裁定 (只读落盘件; 不改任何产物面)。

口径:
- 每臂切片 = [该臂 telemetry-offset-<arm>.txt 记录的字节偏移, 下一臂偏移/文件尾)。
- 轮边界 = 该切片内 `nlp_shape` 事件的顺序 (每轮恰好 1 条; 点位在远端段之后)。
- 远端调用数归到轮: 落在「上一条 nlp_shape 之后 → 本 nlp_shape」窗口内的 `llm_call` 条数 (逐轮切窗, 非整臂总数)。
- 解析失败必须可见 (计数 + 报错), 不静默跳过。
"""
import json
import os
import sys

ROOT = "eval/rover/r581"
TEL = "data/telemetry/host.jsonl"
ARMS = ["A", "B", "N"]


def read_slice(start_off, end_off):
    """按**字节**切片读取 (v2 修正; 见文件尾 CHANGELOG)。

    v1 用文本模式 `f.seek(off); f.read(byte_delta)` —— read() 的入参在文本模式下是
    **字符数**不是字节数 ⇒ 含多字节字符的切片被多读 (实测 arm A 多读 1 条 arm B 事件,
    并在切点处产生 1 条解析失败行, 即 v1 报的 parse_fail=1)。切片边界必须按字节取。
    判据未放宽: 修正只改读法, 预注册 P1..P5 逐字不变。首跑读数留档
    (readings-r581-v1textmode.json / verdict-r581-v1textmode.json), 不翻案。
    """
    rows, parse_fail = [], 0
    with open(TEL, "rb") as f:
        f.seek(start_off)
        data = f.read(end_off - start_off).decode("utf-8", errors="replace")
    for line in data.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            parse_fail += 1
    return rows, parse_fail


def kv(row):
    d = dict(row)
    d.update(d.get("kv") or {})
    return d


def main():
    offs = {}
    for a in ARMS:
        p = os.path.join(ROOT, f"telemetry-offset-{a}.txt")
        offs[a] = int(open(p).read().strip())
    total = os.path.getsize(TEL)
    order = [offs["A"], offs["B"], offs["N"], total]
    out = {"round": "R581", "arms": {}, "parse_fail_total": 0}

    for i, a in enumerate(ARMS):
        rows, pf = read_slice(order[i], order[i + 1])
        out["parse_fail_total"] += pf
        rows = [kv(r) for r in rows]
        shapes = [r for r in rows if r.get("point") == "nlp_shape"]
        turns, prev = [], None
        for s in shapes:
            idx = rows.index(s)
            lo = 0 if prev is None else rows.index(prev) + 1
            win = rows[lo:idx + 1]
            turns.append({
                "n": len(turns) + 1,
                "nlp_shape": {k: s.get(k) for k in
                              ("route", "shape", "face", "basis", "hits", "learned", "shapes", "msg_sha16")},
                "llm_call_n": len([r for r in win if r.get("point") == "llm_call"]),
                "llm_calls": [{k: r.get(k) for k in ("model", "turn", "prompt_tokens", "completion_tokens",
                                                     "success", "content_len", "cache_hit_tokens",
                                                     "cache_miss_tokens", "cache_hit_rate", "agent_session", "ms")}
                              for r in win if r.get("point") == "llm_call"],
                "gate": [{k: r.get(k) for k in ("verdict", "basis", "decided", "prefilter", "prefilter_repeat",
                                                "prefilter_repeat_degrade", "prefilter_nonack", "role")}
                         for r in win if r.get("point") == "local_turn_gate"],
                "gate_cfg": [{k: r.get(k) for k in ("turn_gate_enabled", "local_channel_ready", "repeat_skip", "role")}
                             for r in win if r.get("point") == "local_turn_gate_config"],
                "degrade_remote": [{k: r.get(k) for k in ("reason", "msg_sha16")}
                                   for r in win if r.get("point") in ("repeat_degrade_remote", "paraphrase_degrade_remote")],
                "gate_reject": [r.get("reason") for r in win if r.get("point") == "local_turn_gate_reject"],
                "loop_turn": [{k: r.get(k) for k in ("success", "reply_chars", "intent")}
                              for r in win if r.get("point") == "loop_turn"],
            })
            prev = s
        out["arms"][a] = {"turns": turns, "events": len(rows), "parse_fail": pf}

    A, B, N = (out["arms"][a]["turns"] for a in ARMS)
    gate_cfg_ok = any(g.get("turn_gate_enabled") == "True" and g.get("role") not in (None, "(null)", "")
                      for t in A for g in t["gate_cfg"])
    p1 = [t for t in A if t["nlp_shape"]["shape"] == "1" and t["nlp_shape"]["route"] == "local_skip"
          and t["nlp_shape"]["face"] == "repeat"]
    p2 = bool(p1) and all(t["llm_call_n"] == 0 for t in p1)
    p3_learn = next((t for t in A if int(t["nlp_shape"]["learned"] or 0) >= 1), None)
    p3_evict = next((t for t in B if t["degrade_remote"] and int(t["nlp_shape"]["hits"] or 0) >= 1), None)
    p4 = len([t for t in A if t["nlp_shape"]["shape"] == "1" and t["nlp_shape"]["route"] == "local_skip"]) >= 2
    learn_N = next((t for t in N if int(t["nlp_shape"]["learned"] or 0) > 0), None)
    p5 = bool(N) and all(t["nlp_shape"]["shape"] == "0" for t in N) and learn_N is None

    out["verdict"] = {
        "mech_engaged": gate_cfg_ok,
        "P1_shape_hit_local": "PASS" if p1 else ("VOID" if not gate_cfg_ok else "FAIL"),
        "P1_turns": [t["n"] for t in p1],
        "P2_no_remote_on_hit": "PASS" if p2 else ("VOID" if not p1 else "FAIL"),
        "P2_detail": [{"turn": t["n"], "llm_call_n": t["llm_call_n"]} for t in p1],
        "P3_learned": "PASS" if p3_learn else "FAIL",
        "P3_eviction_invoked": "PASS" if p3_evict else "FAIL",
        "P3_net_decrease": "未测到 (同轮远端成功即重新学到, 预注册已写明该分支不可观测)",
        "P4_generalization": "PASS" if p4 else "FAIL",
        "P5_negative_control": "PASS" if p5 else "FAIL",
        "cost_armA": {"calls": sum(t["llm_call_n"] for t in A),
                      "new_prompt": sum(c["prompt_tokens"] - max(c["cache_hit_tokens"], 0)
                                        for t in A for c in t["llm_calls"] if c["success"]),
                      "completion": sum(c["completion_tokens"] for t in A for c in t["llm_calls"] if c["success"])},
    }
    json.dump(out, open(os.path.join(ROOT, "readings-r581.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(out["verdict"], open(os.path.join(ROOT, "verdict-r581.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(out["verdict"], ensure_ascii=False, indent=1))
    for a in ARMS:
        for t in out["arms"][a]["turns"]:
            print(f"[{a} t{t['n']}] gate={[g.get('basis') + '/' + str(g.get('verdict')) for g in t['gate']]} "
                  f"shape={t['nlp_shape']} calls={t['llm_call_n']} degrade={t['degrade_remote']}")
    print("parse_fail_total =", out["parse_fail_total"])


if __name__ == "__main__":
    main()
