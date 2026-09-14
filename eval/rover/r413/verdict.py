#!/usr/bin/env python3
# R413 判据结算器 —— 只读外部真值 (桩侧 calls-*.jsonl 逐请求落盘 + 门遥测), 不读被测量代码的自报计数器。
# 判据 (预注册 §7.2):
#   C1 远端调用数 相对臂A ↓ >=30%
#   C2 总 token   相对臂A ↓ >=30%
#   C3 负控: 4 条实质轮 (1/3/5/7) 一条都不得被门跳过
#   C4 质量: 被跳过的寒暄轮回复必须 = 非 LLM 模板 (不新增内容, "有回复"不变式)
# 说明: 轮7 在两臂都无远端主调用 —— 链侧澄清拦截 (轮6「嗯。」意图不明 ⇒ 计划停在等你回答), 非门所为,
#       故按"两臂同现的链侧行为"单列, 不计入门的假阴性。
import json, os

D = os.path.dirname(os.path.abspath(__file__))
TURNS = json.load(open(os.path.join(D, "task.json"), encoding="utf-8"))["turns"]
SUBSTANTIVE = [1, 3, 5, 7]   # 预注册: 有新增诉求 ⇒ 必须走远端
CHITCHAT = [2, 4, 6, 8]      # 预注册: 无新增 ⇒ 允许本地消化
TEMPLATE = "收到，继续按当前方向推进，本轮不重新规划。"


def load_turns(p):
    """驱动器产物可能是 JSONL, 也可能是 pretty-print 的单个 JSON (两种都吃)。"""
    if not os.path.exists(p):
        return []
    txt = open(p, encoding="utf-8").read().strip()
    try:
        obj = json.loads(txt)
        return obj if isinstance(obj, list) else obj.get("turns", [obj])
    except json.JSONDecodeError:
        return [json.loads(l) for l in txt.splitlines() if l.strip()]


def budget(arm):
    p = os.path.join(D, f"budget-{arm}.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def last_user_text(call):
    for m in reversed(call.get("messages", [])):
        if m.get("role") == "user":
            return m.get("content") or ""
    return ""


def main():
    out = {}
    a, b = budget("A"), budget("B")
    print("=== 预算 (外部真值: 桩侧逐请求落盘) ===")
    for r in (a, b):
        print(" ", json.dumps(r, ensure_ascii=False) if r else "缺失")

    # 逐轮归属: 取每次远端调用的"最后一条 user 消息"(真发出去的那轮), 与任务脚本比对
    for arm in ("A", "B"):
        calls = [json.loads(l) for l in open(os.path.join(D, f"calls-{arm}.jsonl"), encoding="utf-8") if l.strip()]
        per = {i: 0 for i in range(1, len(TURNS) + 1)}
        for c in calls:
            blob = last_user_text(c)
            for i, t in enumerate(TURNS, 1):
                if t in blob:
                    per[i] += 1
        out[arm] = per
    print("\n=== 逐轮远端主调用 [参考, 不作判据: 后续轮次的历史文本会包含前轮原文 ⇒ 计数偏大] ===")
    for i, t in enumerate(TURNS, 1):
        kind = "实质" if i in SUBSTANTIVE else "寒暄"
        print(f"  轮{i} [{kind}] 臂A={out['A'][i]} 臂B={out['B'][i]}  | {t}")

    turns_b = load_turns(os.path.join(D, "turns-B.jsonl"))
    reply = {r.get("turn") or r.get("index"): (r.get("reply") or "").strip() for r in turns_b}

    # 门遥测 (产品侧观测, 作为"门是否真的在跑"的辅助证据; 判据不以它为分母)
    gate = []
    tel = os.path.join(D, "run-B/data/telemetry/host.jsonl")
    if os.path.exists(tel):
        for l in open(tel, encoding="utf-8"):
            if '"local_turn_gate"' in l:
                k = json.loads(l)["kv"]
                gate.append(k)
    skipped_by_gate = [i for i in range(1, len(TURNS) + 1) if TEMPLATE in reply.get(i, "")]
    # 主判证据 (外部真值一侧): 驱动器**收到**的回复文本 —— 模板串 = 门消化, 否则 = 走了远端/被链侧拦截。
    print("\n=== 逐轮回复性质 (驱动器观测, 外部; 模板 = 门消化) ===")
    for i in range(1, len(TURNS) + 1):
        r = reply.get(i, "")
        tag = "门消化(模板)" if TEMPLATE in r else ("链侧拦截" if i in SUBSTANTIVE and out["A"][i] == 0 else "远端应答")
        print(f"  轮{i}: {tag} | {r[:46]}")

    print("\n=== 门遥测 (臂B) ===")
    for j, k in enumerate(gate, 1):
        print(f"  门#{j}: {k.get('verdict')} | {k.get('basis')} | raw_len={k.get('raw_len')} | role={k.get('role')}")
    print(f"  门驱动 = {len(gate)} 轮; 机械 Pass = {sum(1 for k in gate if 'mechanical' in (k.get('basis') or ''))} / "
          f"r1 判别 = {sum(1 for k in gate if (k.get('basis') or '').startswith('gate:'))}")

    print("\n=== 判据 ===")
    ok = True
    if a and b:
        dc = (a["remote_calls"] - b["remote_calls"]) / a["remote_calls"]
        dt = (a["total_tokens_est"] - b["total_tokens_est"]) / a["total_tokens_est"]
        c1, c2 = dc >= 0.30, dt >= 0.30
        out["d_calls"], out["d_tokens"] = dc, dt
        print(f"  C1 远端调用 ↓ {dc*100:.1f}% (阈值 30%) -> {'PASS' if c1 else 'FAIL'}")
        print(f"  C2 总 token  ↓ {dt*100:.1f}% (阈值 30%) -> {'PASS' if c2 else 'FAIL'}")
        ok &= c1 and c2
    else:
        print("  C1/C2 无法结算 (缺 budget json)"); ok = False

    # C3 负控: 实质轮一条都不得被门跳过。两臂同为 0 调用的轮 = 链侧拦截(非门), 单列并核实其回复非模板。
    chain_intercept = [i for i in SUBSTANTIVE if out["A"][i] == 0 and out["B"][i] == 0 and TEMPLATE not in reply.get(i, "")]
    false_neg = [i for i in SUBSTANTIVE if i in skipped_by_gate]
    c3 = not false_neg
    print(f"  C3 负控: 实质轮被门跳过 = {false_neg or '无'} -> {'PASS' if c3 else 'FAIL'}")
    if chain_intercept:
        print(f"     (单列: 轮{chain_intercept} 两臂皆 0 远端调用 = 链侧澄清拦截, 回复={reply.get(chain_intercept[0], '')[:40]}...)")
    ok &= c3

    # C4 质量: 被跳过轮必须正好是预注册寒暄集, 且回复 == 非 LLM 模板 (不新增内容 + 有回复)
    c4 = sorted(skipped_by_gate) == sorted(CHITCHAT) and all(TEMPLATE in reply.get(i, "") for i in CHITCHAT)
    print(f"  C4 质量: 被门跳过 = {sorted(skipped_by_gate)} (预注册寒暄 {sorted(CHITCHAT)}); "
          f"回复均为非 LLM 模板 = {all(TEMPLATE in reply.get(i, '') for i in CHITCHAT)} -> {'PASS' if c4 else 'FAIL'}")
    ok &= c4

    print(f"\n=== 总结: {'判过' if ok else '判不通过'} ===")
    json.dump({"arm_A": a, "arm_B": b, "per_turn_A": out.get("A"), "per_turn_B": out.get("B"),
               "false_negatives": false_neg, "chain_intercept": chain_intercept,
               "gate": gate, "verdict": "PASS" if ok else "FAIL"},
              open(os.path.join(D, "verdict-r413.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
