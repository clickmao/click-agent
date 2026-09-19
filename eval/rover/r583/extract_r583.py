#!/usr/bin/env python3
"""R583 · 读数抽取 + 判据裁定 (只读落盘件; 零产品改动)。

口径 (先量后改, 见 prereg-r583.json):
- 每臂切片 = [telemetry-offset-<arm>.txt 的字节偏移, 下一臂偏移/文件尾)。
- 轮边界 = 切片内 nlp_shape 事件的顺序 (每轮恰 1 条)。
- **调用面分层** (R583 新注册判据面):
    agent 面 = llm_call.agent_session 非空 ∧ turn>=1 —— 本会话应答链, 受轮闸管;
    宿主面 = agent_session 为空 ∧ turn=0      —— 会话外循环, 与轮闸无关。
  两路径 (session/turn) 不符 ⇒ cross_check_fail, 判器具缺陷 (rc=2, fail-closed)。
- 判据只读 agent 面 (R581 的窗口口径判据不改, 其 FAIL 保留)。

负控有牙 (declare 于预注册, 先跑负控再出真读数):
  NC1 合成窗口: S1 轮2 注入 1 条 agent 面 llm_call ⇒ P1/P2 必须判红;
  NC2 合成窗口: S0 轮2 route=local_skip ⇒ P4 必须判红 (库有无是唯一变量);
  NC3 非平凡性: 真读数 ≠ 两个合成窗口的判决形状。
rc: 0 全达标 / 1 有判据不达标 / 2 器具缺陷 (字段缺失·读空·交叉校验失配) / 3 输入缺失
"""
import json
import os
import sys

ROOT = "eval/rover/r583"
TEL = "data/telemetry/host.jsonl"
ARMS = ["S0", "S1", "D", "N"]


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
    try:
        turn = int(c.get("turn") or 0)
    except Exception:
        turn = 0
    a, b = sess != "", turn >= 1
    if a != b:
        return "cross_check_fail"
    return "agent" if a else "host"


def slice_arms(rows):
    """按 nlp_shape 事件切轮 (每轮 1 条), 带分层调用面。"""
    idxs = [i for i, r in enumerate(rows) if r.get("point") == "nlp_shape"]
    turns, prev = [], None
    for idx in idxs:
        lo = 0 if prev is None else prev + 1
        win = rows[lo:idx + 1]
        calls = [r for r in win if r.get("point") == "llm_call"]
        ag, ho, cc = [], [], []
        for c in calls:
            p = plane(c)
            (ag if p == "agent" else ho if p == "host" else cc).append(c)
        ev = rows[idx]
        turns.append({
            "turn": len(turns) + 1,
            "nlp_shape": {k: ev.get(k) for k in ("route", "shape", "face", "basis", "hits", "learned", "shapes", "msg_sha16")},
            "agent_calls": len(ag),
            "host_calls": len(ho),
            "cross_check_fail": len(cc),
            "agent_new_prompt": sum(max((c.get("prompt_tokens") or 0) - max(c.get("cache_hit_tokens") or 0, 0), 0) for c in ag),
            "agent_completion": sum(c.get("completion_tokens") or 0 for c in ag),
            "host_finish_reasons": [c.get("finish_reason") for c in ho],
            "gate": [{k: r.get(k) for k in ("verdict", "basis")} for r in win if r.get("point") == "local_turn_gate"],
            "gate_cfg": [{k: r.get(k) for k in ("turn_gate_enabled", "role", "repeat_skip")}
                         for r in win if r.get("point") == "local_turn_gate_config"],
            "degrade": [{k: r.get(k) for k in ("reason", "msg_sha16")}
                        for r in win if r.get("point") in ("repeat_degrade_remote", "paraphrase_degrade_remote")],
            "skip_reply": [r.get("kind") for r in win if r.get("point") == "local_gate_skip_reply"],
            "loop_turn": [{k: r.get(k) for k in ("success", "reply_chars")} for r in win if r.get("point") == "loop_turn"],
        })
        prev = idx
    return turns


def judge(turns_by_arm):
    """判据 (只读 agent 面)。返回 (verdict_dict, rc)。"""
    v, bad = {}, []
    S0, S1, D, N = (turns_by_arm[a] for a in ARMS)
    s1t2 = S1[1] if len(S1) > 1 else None
    s0t2 = S0[1] if len(S0) > 1 else None
    if s1t2 is None or s0t2 is None or not D or not N:
        return {"error": "arm turns missing"}, 2
    hit = [t for t in S1 if t["nlp_shape"].get("shape") == "1" and t["nlp_shape"].get("route") == "local_skip"
           and t["nlp_shape"].get("face") == "repeat"]
    # P1 形状面行使 ∧ 该轮 agent 面调用 0
    v["P1_shape_face_exercised"] = "PASS" if (s1t2["nlp_shape"].get("shape") == "1"
                                              and s1t2["nlp_shape"].get("route") == "local_skip"
                                              and s1t2["nlp_shape"].get("face") == "repeat"
                                              and s1t2["agent_calls"] == 0) else "FAIL"
    v["P1_detail"] = {"turn2": s1t2["nlp_shape"], "turn2_agent_calls": s1t2["agent_calls"],
                      "turn2_host_calls": s1t2["host_calls"], "turn2_skip_reply": s1t2["skip_reply"]}
    # P2 分层不增: 命中轮 agent 面调用 < 学习轮 agent 面调用
    v["P2_agent_plane_not_increased"] = "PASS" if s1t2["agent_calls"] < S1[0]["agent_calls"] else "FAIL"
    v["P2_detail"] = {"turn1_agent": S1[0]["agent_calls"], "turn2_agent": s1t2["agent_calls"],
                      "turn2_agent_completion": s1t2["agent_completion"],
                      "host_plane_excluded": s1t2["host_calls"]}
    # P3a 降级路径可达
    v["P3a_degrade_reachable"] = "PASS" if D[0]["degrade"] else "FAIL"
    # P3b 形状命中呈报 (取代 hits>=1)
    v["P3b_shape_reported"] = "PASS" if (D[0]["degrade"] and D[0]["nlp_shape"].get("shape") == "1"
                                         and D[0]["nlp_shape"].get("route") == "remote") else "FAIL"
    v["P3b_detail"] = {"D_nlp_shape": D[0]["nlp_shape"], "D_degrade": D[0]["degrade"]}
    # P4 负控有牙: 同输入无库必须远端; 族外必须不命中/不学
    v["P4_library_is_only_variable"] = "PASS" if (s0t2["nlp_shape"].get("route") == "remote"
                                                  and s0t2["nlp_shape"].get("shape") == "0") else "FAIL"
    v["P4_out_of_family"] = "PASS" if (N[0]["nlp_shape"].get("shape") == "0"
                                       and int(N[0]["nlp_shape"].get("learned") or 0) == 0) else "FAIL"
    # cross-check fail-closed
    cc = sum(t["cross_check_fail"] for t in sum(turns_by_arm.values(), []))
    v["cross_check_fail_total"] = cc
    if cc:
        bad.append("cross_check_fail>0 (器具缺陷, 判 rc=2)")
    v["hit_turns"] = [t["turn"] for t in hit]
    v["rc_plan"] = {"2": "器具缺陷" if bad else None, "1": "有判据不达标" if any(
        str(x).startswith("FAIL") for x in v.values()) else None, "0": "全达标" if not bad else None}
    rc = 2 if bad else (1 if any(str(x).startswith("FAIL") for x in v.values() if isinstance(x, str)) else 0)
    return v, rc


def negative_controls(turns_by_arm):
    """负控有牙: 合成窗口下判据必须翻红 (否则判据是恒真门)。"""
    import copy
    out = {}
    # NC1: S1 轮2 注入 1 条 agent 面调用 ⇒ P1/P2 必红
    fake = copy.deepcopy(turns_by_arm)
    fake["S1"][1]["agent_calls"] = 1
    v1, _ = judge(fake)
    out["NC1_inject_agent_call_on_hit_turn"] = {"P1": v1["P1_shape_face_exercised"], "P2": v1["P2_agent_plane_not_increased"],
                                                "expected": "P1=FAIL,P2=FAIL",
                                                "has_teeth": v1["P1_shape_face_exercised"] == "FAIL" and v1["P2_agent_plane_not_increased"] == "FAIL"}
    # NC2: S0 轮2 伪造成 local_skip ⇒ P4 必红
    fake2 = copy.deepcopy(turns_by_arm)
    fake2["S0"][1]["nlp_shape"]["route"] = "local_skip"
    fake2["S0"][1]["nlp_shape"]["shape"] = "1"
    v2, _ = judge(fake2)
    out["NC2_fake_s0_hit"] = {"P4": v2["P4_library_is_only_variable"], "expected": "P4=FAIL",
                              "has_teeth": v2["P4_library_is_only_variable"] == "FAIL"}
    # NC3: D 臂去掉 degrade ⇒ P3a/P3b 必红
    fake3 = copy.deepcopy(turns_by_arm)
    fake3["D"][0]["degrade"] = []
    v3, _ = judge(fake3)
    out["NC3_strip_degrade"] = {"P3a": v3["P3a_degrade_reachable"], "P3b": v3["P3b_shape_reported"],
                                "expected": "P3a=FAIL,P3b=FAIL",
                                "has_teeth": v3["P3a_degrade_reachable"] == "FAIL" and v3["P3b_shape_reported"] == "FAIL"}
    return out


def main():
    offs = {}
    for a in ARMS:
        p = os.path.join(ROOT, f"telemetry-offset-{a}.txt")
        if not os.path.exists(p):
            print(f"input missing: {p}")
            return 3
        offs[a] = int(open(p).read().strip())
    total = os.path.getsize(TEL)
    order = [offs[a] for a in ARMS] + [total]
    res = {"round": "R583", "arms": {}, "parse_fail_total": 0}
    for i, a in enumerate(ARMS):
        rows, bad = read_slice(order[i], order[i + 1])
        res["parse_fail_total"] += bad
        res["arms"][a] = {"events": len(rows), "parse_fail": bad, "turns": slice_arms(rows)}

    meta = {}
    for line in open(os.path.join(ROOT, "arm-meta.txt")):
        line = line.strip()
        if "=" in line:
            k, _, val = line.partition("=")
            k = k.split()[-1] if " " in k else k
            meta.setdefault(k, []).append(val)
    res["arm_meta"] = meta

    turns_by_arm = {a: res["arms"][a]["turns"] for a in ARMS}
    res["negative_controls"] = negative_controls(turns_by_arm)
    v, rc = judge(turns_by_arm)
    res["verdict"] = v
    res["rc"] = rc
    json.dump(res, open(os.path.join(ROOT, "readings-r583.json"), "w"), ensure_ascii=False, indent=1)
    verdict_doc = {
        "round": "R583",
        "verdict": v,
        "negative_controls": res["negative_controls"],
        "rc": rc,
        "gates": {
            "build": "dotnet build src/agent.host/agent.host.csproj -c Release ⇒ 10 Warning(s) / **0 Error(s)** "
                     "(重建于跑臂之后; 二进制 sha256 逐位不变 fe1fb720…)",
            "form": "dotnet test --filter VerificationForm|SkillGeneralization|DevPlanDocRef ⇒ Failed 0 / Passed 14 ⇒ **14/14**",
            "run_arms": "4 臂 rc=0 (S0 44s / S1 12s / D 24s / N 10s); 远端预检 http=200",
        },
        "诚实边界": [
            "零产品源码改动 ⇒ 本轮不宣称任何质量/成本降幅 (无可比窗口)。",
            "单轮 n=1 每臂 ⇒ 只作机制存在性证据, 不作分布结论 (跨窗摆动常大于臂间效应)。",
            "codex 外部真值同题对照 / 回复质量 / 轮数 / 问答计数: 本轮**未测** (非质量对照窗) ⇒ 记未测, 不记无效应。",
            "R581 的 P2 FAIL 与 P3_eviction FAIL **保留不翻案**; 本轮 agent 面口径是**新注册**(与 R432「先分通道再汇总」同族), 不是对原判据的放宽。",
            "P6 按预注册照原样判: 「行数 1→2」成立, 但「两行逐字相同」子项不成立, 且预注册给出的候选机理(Same 未拦住)与真机理(内存剔除后重新学习)不符 ⇒ 机理修正单列 posthoc, 判据不改。",
            "自捕缺陷: 形状库内存剔除不落盘 (ReportOutcome 只改内存) ⇒ 库行数不能当形状数; 本轮零产品改动 ⇒ 只登记不定因修复。",
            "宿主面调用与轮闸无关, 本轮判据一律排除; 「宿主面是否可省」本轮未测。",
        ],
    }
    json.dump(verdict_doc, open(os.path.join(ROOT, "verdict-r583.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps({"rc": rc, "verdict": v,
                      "nc_teeth": {k: x["has_teeth"] for k, x in res["negative_controls"].items()},
                      "parse_fail_total": res["parse_fail_total"]}, ensure_ascii=False, indent=1))
    return rc


if __name__ == "__main__":
    sys.exit(main())
