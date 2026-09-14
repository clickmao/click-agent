#!/usr/bin/env python3
"""R424 判据结算器 —— 只读外部真值（桩侧逐请求落盘 + 驱动器观测 + 遥测），不读被测量代码自报计数器。

判据（预注册 docs/plans/v0.45.0-r424-aot-mainline-replication.md §3）:
  V0 形态闸: 被测二进制 = AOT 原生（prov-B.json）, 且负控（IL apphost）确有判别力
  V1 门真身: 臂B 遥测 local_turn_gate_config{turn_gate_enabled, local_channel_ready, role} ∧ gate:* 事件 ≥1
  V2 无效跑: 臂B 读数不得与臂A 逐位相同; 跳过轮 ≥1
  C1 远端调用 ↓≥30% (分母=臂A)   C2 远端 token ↓≥30%
  C3 假阴性: 实质轮(1/3/5/7) 不得被门跳过     C4 质量: 每轮 ok ∧ 回复非空; 跳过轮回复=非LLM模板
  C5 无设备零回归: 臂BP calls == 臂A calls ∧ token 差 ≤5% ∧ 跳过轮 0
  C6 r1 归因: 省下的调用数 == 非实质轮数, 且臂BP(无r1)增益归零
"""
import hashlib
import json
import os

D = os.path.dirname(os.path.abspath(__file__))
ALIAS = "/tmp/pub_r424/agenthost"   # 同字节归档副本（防同名发布目录被后续覆盖）


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


ALIAS_SHA = _sha256(ALIAS) if os.path.exists(ALIAS) else None

TASK = json.load(open(os.path.join(D, "task.json"), encoding="utf-8"))
TURNS = TASK["turns"]
SUBSTANTIVE = [1, 3, 5, 7]
CHITCHAT = [2, 4, 6, 8]
TEMPLATE = "收到，继续按当前方向推进，本轮不重新规划。"


def budget(arm):
    p = os.path.join(D, f"budget-{arm}.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def load_turns(arm):
    p = os.path.join(D, f"turns-{arm}.jsonl")
    if not os.path.exists(p):
        return []
    txt = open(p, encoding="utf-8").read().strip()
    try:
        obj = json.loads(txt)
        return obj if isinstance(obj, list) else obj.get("turns", [obj])
    except json.JSONDecodeError:
        return [json.loads(l) for l in txt.splitlines() if l.strip()]


def calls(arm):
    p = os.path.join(D, f"calls-{arm}.jsonl")
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()] if os.path.exists(p) else []


def attribute(arm):
    """按绝对时间窗把每次远端调用归属到轮（R423 修 R418「归属缺失」：窗内计数, 不做子串匹配）。"""
    rows = calls(arm)
    turns = load_turns(arm)
    per = {i: 0 for i in range(1, len(TURNS) + 1)}
    unattr = 0
    for r in rows:
        ts = r.get("ts")
        if ts is None:
            unattr += 1
            continue
        hit = None
        for t in turns:
            if t.get("t_start") is not None and t.get("t_end") is not None and t["t_start"] <= ts <= t["t_end"]:
                hit = t["turn"]
                break
        if hit is None:
            unattr += 1
        else:
            per[hit] += 1
    return per, unattr


def telemetry(arm):
    tel = os.path.join(D, f"run-{arm}/data/telemetry/host.jsonl")
    cfg, gate = None, []
    if os.path.exists(tel):
        for l in open(tel, encoding="utf-8"):
            if '"local_turn_gate_config"' in l:
                cfg = json.loads(l)["kv"]
            elif '"local_turn_gate"' in l:
                gate.append(json.loads(l)["kv"])
    return cfg, gate


def main():
    a, b, bp = budget("A"), budget("B"), budget("BP")
    prov = None
    pp = os.path.join(D, "prov-B.json")
    if os.path.exists(pp):
        prov = json.load(open(pp, encoding="utf-8"))

    print("=== 被测二进制身份（读数绑定）===")
    for nm, bd in (("A", a), ("B", b), ("BP", bp)):
        if bd:
            print(f"  臂{nm}: {bd['binary']} bytes={bd['binary_bytes']} sha256={bd['binary_sha256'][:12]}")
    print("\n=== 预算（外部真值: 桩侧逐请求落盘）===")
    for nm, bd in (("A", a), ("B", b), ("BP", bp)):
        print(f"  臂{nm}: {json.dumps(bd, ensure_ascii=False) if bd else '缺失'}")

    print("\n=== 逐轮远端调用（时间窗归属, 外部真值）===")
    pa, ua = attribute("A")
    pb, ub = attribute("B")
    ppb, upb = attribute("BP") if bp else ({i: 0 for i in range(1, len(TURNS) + 1)}, 0)
    for i, t in enumerate(TURNS, 1):
        kind = "实质" if i in SUBSTANTIVE else "寒暄"
        print(f"  轮{i} [{kind}] A={pa[i]} B={pb[i]} BP={ppb[i]} | {t}")
    print(f"  (未归属: A={ua} B={ub} BP={upb})")

    print("\n=== 逐轮回复性质（驱动器观测, 外部）===")
    rep = {arm: {r["turn"]: (r.get("reply") or "").strip() for r in load_turns(arm)} for arm in ("A", "B", "BP")}
    secs = {arm: {r["turn"]: r.get("secs") for r in load_turns(arm)} for arm in ("A", "B", "BP")}
    for arm in ("A", "B", "BP"):
        print(f"  --- 臂{arm} ---")
        for i in range(1, len(TURNS) + 1):
            r = rep[arm].get(i, "")
            tag = "门消化(模板)" if TEMPLATE in r else "远端应答"
            print(f"    轮{i}: {tag} secs={secs[arm].get(i)} len={len(r)} | {r[:44]}")

    cfgB, gateB = telemetry("B")
    cfgBP, _ = telemetry("BP")
    print("\n=== 门遥测 ===")
    print(f"  臂B config: {json.dumps(cfgB, ensure_ascii=False) if cfgB else '缺失'}")
    print(f"  臂BP config: {json.dumps(cfgBP, ensure_ascii=False) if cfgBP else '缺失'}")
    print(f"  臂B local_turn_gate 事件: {len(gateB)}  (机械 Pass={sum(1 for k in gateB if 'mechanical' in (k.get('basis') or ''))}, "
          f"r1 判别={sum(1 for k in gateB if (k.get('basis') or '').startswith('gate:'))})")
    for j, k in enumerate(gateB, 1):
        print(f"    门#{j}: verdict={k.get('verdict')} basis={k.get('basis')} raw_len={k.get('raw_len')} err={k.get('error')}")

    checks = {}

    def chk(name, cond, detail=""):
        checks[name] = {"pass": bool(cond), "detail": detail}
        print(f"  {name}: {'PASS' if cond else 'RED'}  {detail}")
        return bool(cond)

    print("\n=== 判据 ===")
    v0d = "缺 prov-B.json"
    if prov:
        ut = prov.get("under_test") or {}
        v0d = (f"bytes={ut.get('bytes')} bare_stdout={str(ut.get('bare_stdout_head'))[:40]!r} "
               f"needs_runtime={ut.get('needs_runtime')} neg_ok={prov.get('neg_ok')}")
    v0 = chk("V0 形态闸(AOT)", bool(prov) and bool((prov.get("under_test") or {}).get("native_ok")) and bool(prov.get("neg_ok")), v0d)
    v1 = chk("V1 门真身", bool(cfgB) and cfgB.get("turn_gate_enabled") == "True"
             and cfgB.get("local_channel_ready") == "True" and cfgB.get("role") not in (None, "", "(null)")
             and sum(1 for k in gateB if (k.get("basis") or "").startswith("gate:")) >= 1,
             f"config={cfgB} gate_events={len(gateB)}")
    skipped = {arm: sorted(i for i in range(1, len(TURNS) + 1) if TEMPLATE in rep[arm].get(i, "")) for arm in ("A", "B", "BP")}
    v2 = chk("V2 无效跑闸", bool(a and b) and not (a["remote_calls"] == b["remote_calls"] and a["total_tokens_est"] == b["total_tokens_est"])
             and len(skipped["B"]) >= 1,
             f"A=({a['remote_calls']},{a['total_tokens_est']}) B=({b['remote_calls']},{b['total_tokens_est']}) skippedB={skipped['B']}")

    dc = dt = None
    if a and b and a["remote_calls"]:
        dc = (a["remote_calls"] - b["remote_calls"]) / a["remote_calls"]
        dt = (a["total_tokens_est"] - b["total_tokens_est"]) / a["total_tokens_est"]
    c1 = chk("C1 远端调用 ↓≥30%", dc is not None and dc >= 0.30, f"{dc*100:.1f}%" if dc is not None else "无法结算")
    c2 = chk("C2 远端 token ↓≥30%", dt is not None and dt >= 0.30, f"{dt*100:.1f}%" if dt is not None else "无法结算")
    fn = [i for i in SUBSTANTIVE if i in skipped["B"]]
    c3 = chk("C3 假阴性=0", not fn, f"被门跳过的实质轮={fn or '无'}")
    c4 = (sorted(skipped["B"]) == sorted(CHITCHAT)
          and all((rep["B"].get(i) or "").strip() for i in range(1, len(TURNS) + 1))
          and all(r.get("ok") for r in load_turns("B")))
    chk("C4 质量(模板+非空+ok)", c4, f"skippedB={sorted(skipped['B'])} 预注册寒暄={sorted(CHITCHAT)}")
    c5_ok = False
    if a and bp:
        c5_ok = (bp["remote_calls"] == a["remote_calls"]
                 and abs(bp["total_tokens_est"] - a["total_tokens_est"]) / max(1, a["total_tokens_est"]) <= 0.05
                 and len(skipped["BP"]) == 0)
    chk("C5 无设备零回归(臂BP≡臂A)", c5_ok,
        f"BP=({(bp or {}).get('remote_calls','?')},{(bp or {}).get('total_tokens_est','?')}) A=({a['remote_calls']},{a['total_tokens_est']}) skippedBP={skipped['BP']}")
    saved = (a["remote_calls"] - b["remote_calls"]) if (a and b) else None
    chk("C6 r1 归因", saved is not None and saved == len(CHITCHAT), f"省下调用={saved} 非实质轮={len(CHITCHAT)}")

    # ── 事后判据 (R422 纪律: 与预注册主判据**分列**, 不得混入 verdict 依据) ──
    post = {}
    print("\n=== 事后检查 (checks_posthoc; 不参与 verdict) ===")
    def pchk(name, cond, detail=""):
        post[name] = {"pass": bool(cond), "detail": detail, "posthoc": True}
        print(f"  {name}: {'PASS' if cond else 'RED'}  {detail}")
    nb = [i for i in range(1, len(TURNS) + 1) if i not in skipped["B"]]
    same = all(rep["A"].get(i) == rep["B"].get(i) for i in nb)
    pchk("P1 质量无回归(非跳过轮回复逐字节同臂A)", same, f"比对轮={nb} 差异轮={[i for i in nb if rep['A'].get(i) != rep['B'].get(i)]}")
    sysB = ""
    for r in calls("B"):
        for m in r.get("messages") or []:
            if m.get("role") == "system":
                sysB = m.get("content") or ""
                break
        if sysB:
            break
    seed_hit = "你是一个低调但执着的追问者" in sysB
    pchk("P2 role 额外数据真挂载(ProfileSeed 非空)", seed_hit and cfgB is not None and cfgB.get("role") == "skeptic",
         f"roleSeed 来源=IndustrialAgentV2.cs:1481 ActiveRole.Id+'|'+Clip(ProfileSeed,80); 远端系统提示含 ProfileSeed 片段={seed_hit}; 门遥测 role={cfgB and cfgB.get('role')}")
    deg = [k for k in telemetry("BP")[1] if k.get("decided") == "false" and k.get("error")]
    pchk("P3 失败可见性(无设备真机)", len(deg) == len(CHITCHAT) and all("degraded" in (k.get("basis") or "") for k in deg),
         f"decided=false 且带 error 的门事件={len(deg)}/{len(CHITCHAT)} 例: {deg[0].get('error') if deg else '-'} basis={deg[0].get('basis') if deg else '-'}")
    raws = [k.get("raw") or "" for k in gateB if (k.get("basis") or "").startswith("gate:")]
    pair = list(zip([TURNS[i - 1] for i in skipped["B"]], raws))
    hit = [t in r for t, r in pair]
    pchk("P4 r1 读到本轮用户原文", bool(pair) and all(hit), f"Skip 事件 raw 内用户原文命中={hit}")
    pchk("P5 归属完整性", b is not None and ua == 0 and ub == 0 and upb == 0 and sum(pb.values()) == b["remote_calls"],
         f"未归属 A={ua}/B={ub}/BP={upb}; 逐轮归属和在轮边界对异步判官调用存在 ±1 轮滑移(总量精确)")

    invalid = not (v0 and v1 and v2 and c5_ok)
    verdict = "INVALID" if invalid else ("PASS" if all(checks[k]["pass"] for k in checks) else "FAIL")
    print(f"\n=== 总结: {verdict} ===")
    print(f"  (形态/仪器闸 = {'全绿' if not invalid else '有红 ⇒ 读数不可作判据'}); 省下调用={saved} 调用↓{dc*100:.1f}% token↓{dt*100:.1f}%"
          if dc is not None else "")

    json.dump({"round": "R424", "binary": (b or {}).get("binary"), "binary_sha256": (b or {}).get("binary_sha256"),
               "artifact_alias": ALIAS,
               "artifact_alias_sha256": ALIAS_SHA,
               "artifact_alias_same_sha256": (b or {}).get("binary_sha256") == ALIAS_SHA,
               "arm_A": a, "arm_B": b, "arm_BP": bp,
               "per_turn_A": pa, "per_turn_B": pb, "per_turn_BP": ppb, "unattributed": {"A": ua, "B": ub, "BP": upb},
               "skipped": skipped, "false_negatives": fn,
               "gate_B_config": cfgB, "gate_B": gateB, "gate_BP_config": cfgBP,
               "prov": prov, "checks": checks, "checks_pre_registered": True,
               "checks_posthoc": post, "posthoc_participates_in_verdict": False,
               "d_calls": dc, "d_tokens": dt, "verdict": verdict},
              open(os.path.join(D, "verdict-r424.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("[written] verdict-r424.json")


if __name__ == "__main__":
    main()
