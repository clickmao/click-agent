#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R492 判据器 (派生: 复用 R491 判据函数, 只换臂集/对照臂/新增不变量; 通用代码逻辑, 语言无关)

臂矩阵: TC (pair_trim=off, 同窗对照) vs TP1/TP2/TP3 (pair_trim=on) —— 同一 AOT 产物/夹具/窗。

不变量 (逐个机检, fail-closed):
  I0  臂可跑 (未跑即 FAIL; 无静默豁免)
  I1  声明面逐调用可观测 (tool_decl_gate rows > 0)
  I2  tool_decl_gate 门态与 flags 一致
  I3  无声明面违规 (门开不下发 / 门关必下发)
  I4  回放面模板串 == 0 (模板答复不进远端)
  I5  处理臂剪裁打点 > 0 (确有剪裁触发; 对照臂免)
  I6  回放配对闸门态与臂参一致 —— **人面 on 必须落成遥测 1** (直传 "on" 会静默当关的假阴性陷阱)
  I7  处理臂 pair_face.skip_user_leak == 0 (H2)
  I8  对照臂 skip_user_leak >= 10 (H1; 不成立 ⇒ 本轮判据不适用, 记 non-blocking)
  I9  处理臂付费 token <= 对照臂 (H4; 同窗单变量, 不升)
  I10 四臂 12 轮无空答复 (H5)

用法: python3 analyze_r492.py [--json eval/rover/r492/verdict-r492.json]
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "r491"))
import analyze_r491 as base  # noqa: E402

base.HERE = HERE            # 全部读取面切到本回合目录 (r491 目录只作代码来源)
ARMS = [("TC", "TC"), ("TP1", "TP1"), ("TP2", "TP2"), ("TP3", "TP3")]
TREAT = ("TP1", "TP2", "TP3")
CTRL = "TC"
OUT_OF_SCOPE = {}


def _b(x):
    return x if isinstance(x, bool) else str(x).lower() in ("true", "1")


def leak_split(key):
    """post·hoc 面 (非预注册判据): 把 skip_user_leak 拆成「活轮」与「陈轮」。

    机制事实: 该计数器 = 内容里含本地模板串的用户消息数 (子串代理, 非结构量)。
      · 活轮 = 每个请求的**最后一个** user 消息 —— 是当前输入, 内嵌上轮模板属正常, 不可能剪掉;
      · 陈轮 = 其余 user 消息 —— 其中「本地模板轮」的 user 侧才应被配对剪裁移除。
    ⇒ 验收应看结构量 (user->user 相邻对 0, 剪裁打点 >0), 而非该子串计数。
    """
    calls = base.rows(os.path.join(HERE, "calls-%s.jsonl" % key))
    stale = live = 0
    for c in calls:
        ms = base._msgs(c)
        uidx = [i for i, m in enumerate(ms) if m.get("role") == "user"]
        if not uidx:
            continue
        last = uidx[-1]
        for i in uidx:
            if base.TEMPLATE in (ms[i].get("content") or ""):
                if i == last:
                    live += 1
                else:
                    stale += 1
    return {"leak_stale": stale, "leak_live": live}


def main():
    out = {"round": "R492", "arms": {}, "invariants": [], "deltas": {}}
    for arm, key in ARMS:
        if not os.path.exists(os.path.join(HERE, "usage-%s.jsonl" % key)):
            pf = os.path.join(HERE, "preflight-%s.json" % key)
            reason = "no_usage_file"
            if os.path.exists(pf):
                d = json.load(open(pf, encoding="utf-8"))
                reason = "起手闸 %s: %s (mem_available_mb=%s < gate_mb=%s)" % (
                    d.get("verdict"), d.get("blocker_cause"), d.get("mem_available_mb"), d.get("gate_mb"))
            out["arms"][arm] = {"not_run": True, "reason": reason}
            continue
        st = base.arm_stats(key)
        st["key"] = key
        st["replay"] = base.replay_scan(key)
        st["gate"] = base.gate_scan(key)
        st["quality"] = base.quality_scan(key)
        st["pair"] = base.pair_face(key)
        fl = os.path.join(HERE, "flags-%s.json" % key)
        st["flags"] = json.load(open(fl, encoding="utf-8")) if os.path.exists(fl) else None
        out["arms"][arm] = st

    def pct(a, b):
        return round((a - b) / b * 100, 2) if b else None

    def ran(arm):
        return not out["arms"][arm].get("not_run")

    C = out["arms"][CTRL] if ran(CTRL) else None
    for arm in TREAT:
        a = out["arms"][arm]
        if a.get("not_run") or C is None:
            out["deltas"][arm] = {"not_run": True,
                                  "reason": a.get("reason", "对照臂未跑 ⇒ 无同窗分母")}
            continue
        out["deltas"][arm] = {
            "calls": "%d→%d (%s%%)" % (C["calls"], a["calls"], pct(a["calls"], C["calls"])),
            "total_tokens": "%d→%d (%s%%)" % (C["total"], a["total"], pct(a["total"], C["total"])),
            "prompt_tokens": "%d→%d (%s%%)" % (C["prompt"], a["prompt"], pct(a["prompt"], C["prompt"])),
            "cost_cny": "%s→%s (%s%%)" % (C["cost"], a["cost"], pct(a["cost"], C["cost"])),
            "skip_user_leak": "%d→%d" % (C["pair"]["skip_user_leak"], a["pair"]["skip_user_leak"]),
        }
    rtl = [out["arms"][x]["total"] for x in TREAT if ran(x)]
    if rtl and C is not None:
        out["deltas"]["T_spread"] = {
            "arms": [x for x in TREAT if ran(x)],
            "total_tokens": "%d..%d (min..max)" % (min(rtl), max(rtl)),
            "worst_case_vs_ctrl_pct": pct(max(rtl), C["total"]),
            "best_case_vs_ctrl_pct": pct(min(rtl), C["total"]),
        }

    for arm, key in ARMS:
        a = out["arms"][arm]
        ev = lambda k, d: {"id": k, "arm": arm, "pass": bool(d), "evidence": ""}
        if a.get("not_run"):
            out["invariants"].append({"id": "I0_臂可跑", "arm": arm, "pass": False,
                                      "blocking": arm not in OUT_OF_SCOPE, "evidence": a["reason"]})
            continue
        fl = a["flags"] or {}
        td_on = fl.get("tool_decl_gate") == "on"
        pt_on = fl.get("replay_pair_trim") == "on"
        pg = a["pair"]["pair_gate"]
        want_pg = ["1"] if pt_on else ["0"]
        out["invariants"].append({"id": "I0_臂可跑", "arm": arm, "pass": True, "evidence": "usage rows=%d" % a["calls"]})
        out["invariants"].append({"id": "I1_声明面逐调用可观测", "arm": arm, "pass": a["gate"]["rows"] > 0,
                                  "evidence": "tool_decl_gate rows=%d by_reason=%s" % (a["gate"]["rows"], a["gate"]["by_reason"])})
        out["invariants"].append({"id": "I2_声明门与臂参一致", "arm": arm,
                                  "pass": set(a["gate"]["gate_values"]) == ({"1"} if td_on else {"0"}),
                                  "evidence": "flags.tool_decl_gate=%s 遥测=%s" % (fl.get("tool_decl_gate"), a["gate"]["gate_values"])})
        out["invariants"].append({"id": "I3_无声明面违规", "arm": arm, "pass": len(a["gate"]["violations"]) == 0,
                                  "evidence": "violations=%d %s" % (len(a["gate"]["violations"]), a["gate"]["violations"][:2])})
        out["invariants"].append({"id": "I4_模板串不进远端", "arm": arm,
                                  "pass": a["replay"]["assistant_template_msgs"] == 0,
                                  "evidence": "requests=%d tmpl_msgs=%d user_user_adj=%d" % (
                                      a["replay"]["requests"], a["replay"]["assistant_template_msgs"],
                                      a["replay"]["user_user_adjacent_pairs"])})
        out["invariants"].append({"id": "I5_剪裁打点非零", "arm": arm,
                                  "pass": a["gate"]["replay_trimmed_sum"] > 0 or not pt_on,
                                  "evidence": "replay_trimmed_calls=%d sum=%d (flags.replay_pair_trim=%s)" % (
                                      a["gate"]["replay_trimmed_calls"], a["gate"]["replay_trimmed_sum"], fl.get("replay_pair_trim"))})
        out["invariants"].append({"id": "I6_配对闸门态与臂参一致", "arm": arm,
                                  "pass": pg == want_pg,
                                  "evidence": "flags.replay_pair_trim=%s ⇒ 期望遥测 replay_pair_gate=%s, 实得=%s (人面 on 必须落成 1)" % (
                                      fl.get("replay_pair_trim"), want_pg, pg)})
        if pt_on:
            out["invariants"].append({"id": "I7_处理臂无 user 侧泄漏", "arm": arm,
                                      "pass": a["pair"]["skip_user_leak"] == 0,
                                      "evidence": "skip_user_leak=%d user_trimmed=%d" % (
                                          a["pair"]["skip_user_leak"], a["pair"]["user_trimmed"])})
        else:
            out["invariants"].append({"id": "I8_对照臂有可剪泄漏", "arm": arm,
                                      "pass": a["pair"]["skip_user_leak"] >= 10,
                                      "blocking": False,
                                      "evidence": "skip_user_leak=%d (不足 ⇒ 本轮判据不适用, 记 non-blocking)" % a["pair"]["skip_user_leak"]})
        if pt_on and C is not None:
            out["invariants"].append({"id": "I9_付费token不升", "arm": arm, "pass": a["total"] <= C["total"],
                                      "evidence": "TP total=%d vs TC total=%d (%s%%)" % (
                                          a["total"], C["total"], pct(a["total"], C["total"]))})
        empt = (a["quality"]["classes"] or {}).get("empty", 0)
        out["invariants"].append({"id": "I10_无空答复", "arm": arm, "pass": empt == 0,
                                  "evidence": "turns=%d classes=%s" % (a["quality"]["turns"], a["quality"]["classes"])})

    mine = [i for i in out["invariants"] if i.get("blocking", True)]
    ok = all(i["pass"] for i in mine)
    out["verdict"] = "PASS" if ok else "FAIL"
    out["arms_run"] = [a for a, _ in ARMS if ran(a)]
    # ---- post·hoc 面 (单列; 不改预注册判据, 只作机制解释) ----
    out["checks_posthoc"] = {
        "note": "I7 的 skip_user_leak 是**子串代理**而非结构量: 每请求最后一个 user(活轮)内嵌上轮模板属正常输入, 不可能剪掉 ⇒ 该判据结构性不可达 0。",
        "leak_split": {a: leak_split(k) for a, k in ARMS if ran(a)},
        "struct_face": {a: {"user_user_adj": out["arms"][a]["pair"]["user_user_adj"],
                            "user_trimmed": out["arms"][a]["pair"]["user_trimmed"],
                            "trim_stamps": out["arms"][a]["gate"]["replay_trimmed_sum"]}
                        for a, _ in ARMS if ran(a)},
    }
    dst = os.path.join(HERE, "verdict-r492.json")
    if "--json" in sys.argv:
        dst = sys.argv[sys.argv.index("--json") + 1]
    open(dst, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    for arm, _ in ARMS:
        a = out["arms"][arm]
        if a.get("not_run"):
            print("[%s] NOT_RUN: %s" % (arm, a["reason"]))
            continue
        print("[%s] calls=%d total=%d prompt=%d completion=%d empty_body=%d cost=%s pair=%s"
              % (arm, a["calls"], a["total"], a["prompt"], a["completion"], a["empty_body"], a["cost"],
                 {k: a["pair"][k] for k in ("user_trimmed", "pair_gate", "user_user_adj", "skip_user_leak")}))
        print("      quality: classes=%s false_premise_pass=%s" % (
            (a["quality"]["classes"]), (a["quality"]["false_premise"] or {}).get("pass")))
    for k, v in out["deltas"].items():
        print("[delta %s] %s" % (k, v))
    print("[invariants] %s (arms_run=%s)" % ("PASS" if ok else "FAIL", out["arms_run"]))
    for i in out["invariants"]:
        if not i["pass"]:
            print("   RED%s %s/%s: %s" % ("" if i.get("blocking", True) else "(non-blocking)", i["id"], i["arm"], i["evidence"]))
    print("[json] %s" % dst)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
