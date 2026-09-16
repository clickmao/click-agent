#!/usr/bin/env python3
# R494 收口断言 (fail-closed) —— "声明面通道轴"的**实发面**证据。
#
# 判据层级 (禁含糊):
#   HARD-1  请求面: 隔离通道调用 (用户消息含 [微步骤隔离问询] / system 为一次性隔离器)
#           在通道轴 on 时 tools_n 必须 == 0; 通道轴 off 时必须**复现泄漏** (存在 tools_n>0 的隔离调用,
#           除非上游本轮恰好没请求工具 ⇒ 记 unreported, 不算通过)。
#   HARD-2  遥测 schema: 通道轴 on 且存在隔离调用 ⇒ telemetry 里必须有
#           point=tool_decl_gate 且 kv.isolated_channel=true 的事件。
#           **没有 = 打点与实发面脱钩** (R490 replay_trimmed 同类缺陷) ⇒ 红。
#   SOFT    逐事件一致性: 凡 kv.isolated_channel=true 的事件, declared 必须 false 且
#           reason == isolated_channel_drop; 不一致 ⇒ 红 (与 HARD-1 同源, 分开报便于定位)。
# 退出码: 0 = 全绿; 13 = 红; 14 = 数据缺失 (夹具/器具问题, 与判据无关)。
import argparse, json, os, sys

def load_jsonl(p):
    out = []
    if not os.path.exists(p):
        return out
    with open(p, encoding="utf-8-sig") as f:
        for l in f:
            l = l.strip()
            if l:
                out.append(json.loads(l))
    return out

ISO_MARK = "微步骤隔离问询"
ISO_SYS = ("你是隔离执行的微步骤助手", "你是一个一次性隔离子任务执行器")

def is_isolated(row):
    msgs = row.get("messages") or []
    for m in msgs:
        c = m.get("content")
        if not isinstance(c, str):
            continue
        if ISO_MARK in c:
            return True
        if m.get("role") == "system" and any(s in c for s in ISO_SYS):
            return True
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--channel", required=True, choices=["on", "off"])
    ap.add_argument("--out", default=None, help="证据落盘路径 (默认 <dir>/assert-face-<arm>.txt)")
    a = ap.parse_args()
    a.out = a.out or os.path.join(a.dir, "assert-face-%s.txt" % a.arm)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    a._log = open(a.out, "w", encoding="utf-8")
    d = a.dir
    def say(msg):
        print(msg)
        a._log.write(msg + "\n")
        a._log.flush()
    calls = load_jsonl(os.path.join(d, "calls-%s.jsonl" % a.arm))
    tel = load_jsonl(os.path.join(d, "tel-%s" % a.arm, "host.jsonl"))
    if not calls:
        say("[assert-face] 数据缺失: calls-%s.jsonl 为空" % a.arm)
        return 14
    if not tel:
        say("[assert-face] 数据缺失: tel-%s/host.jsonl 为空 (遥测未落盘)" % a.arm)
        return 14
    iso = [r for r in calls if is_isolated(r)]
    iso_tools = [r for r in iso if int(((r.get("sampling") or {}).get("tools_n") or 0)) > 0]
    tg = [r for r in tel if r.get("point") == "tool_decl_gate"]
    tg_iso = [r for r in tg if (r.get("kv") or {}).get("isolated_channel") is True]
    rec = {"schema": "r494-assert-face/1", "arm": a.arm, "channel": a.channel,
           "calls": len(calls), "iso_calls": len(iso), "iso_calls_with_tools": len(iso_tools),
           "iso_seqs": [r.get("seq") for r in iso],
           "iso_tools_seqs": [r.get("seq") for r in iso_tools],
           "tg_events": len(tg), "tg_iso_events": len(tg_iso), "red": [], "notes": []}
    say("[assert-face] arm=%s channel=%s 远端调用=%d 隔离通道调用=%d 其中带工具=%d | tool_decl_gate事件=%d 带isolated_channel=%d"
          % (a.arm, a.channel, len(calls), len(iso), len(iso_tools), len(tg), len(tg_iso)))
    red = []
    if a.channel == "on":
        if iso_tools:
            red.append("HARD-1: 通道轴 on 但 %d 条隔离调用仍下发工具 (seq=%s)"
                       % (len(iso_tools), [r.get("seq") for r in iso_tools][:8]))
        if not iso:
            rec["notes"].append("无隔离通道调用 ⇒ HARD-1 判据未被触发 (unreported, 不得称通过)")
            say("[assert-face] 注意: 本轮无隔离通道调用 ⇒ HARD-1 判据**未被触发** (记 unreported, 不得称通过)")
        elif not tg_iso:
            red.append("HARD-2: 通道轴 on 且隔离调用 %d 条, 但遥测无 kv.isolated_channel=true 事件 ⇒ 打点与实发面脱钩" % len(iso))
    else:
        if iso and not iso_tools:
            rec["notes"].append("通道轴 off: 隔离 %d 条但无一带工具 ⇒ 泄漏未复现 (上游未请求工具; unreported)" % len(iso))
            say("[assert-face] 通道轴 off: 隔离调用 %d 条但无一条带工具 ⇒ 泄漏未复现 (上游本轮未请求工具; 记 unreported)" % len(iso))
        elif iso_tools:
            rec["notes"].append("通道轴 off: 泄漏复现已观测 (%d 条带工具)" % len(iso_tools))
    # SOFT 只对**通道轴 on**成立 (通道轴 off 时隔离事件应当 declared=true = 泄漏复现本身)
    if a.channel == "on":
        for r in tg_iso:
            kv = r.get("kv") or {}
            if kv.get("declared") is not False or kv.get("reason") != "isolated_channel_drop":
                red.append("SOFT: 事件不一致 declared=%s reason=%s" % (kv.get("declared"), kv.get("reason")))
    rec["red"] = red
    rec["verdict"] = "PASS" if not red else "FAIL"
    for m in red:
        say("[assert-face][红] " + m)
    say("[assert-face] " + rec["verdict"])
    jp = os.path.join(d, "assert-face-%s.json" % a.arm)
    json.dump(rec, open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    say("[assert-face] → " + jp)
    a._log.close()
    return 0 if not red else 13

if __name__ == "__main__":
    sys.exit(main())
