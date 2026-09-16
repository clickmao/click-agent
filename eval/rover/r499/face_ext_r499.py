#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R499 扩展面判据 (三个新面, fail-closed)。

  HARD-3b 打点面真值收口 (候选①): 打点文件里不得出现任何 raw 账本码字面量,
          且 local_decision_ledger 点的 kv 必须只带指纹 (code8 + key_id), 不得带 code。
  HARD-6  越界拒绝见证 + canary 面 (候选③):
          文件面 = WorkspaceActionPort.P1 边界 (恒开, 无开关) ⇒ 拒绝见证 "路径越界";
          命令面 = AGENTFRAMEWORK_ACTION_BOUNDARY ⇒ AB=on 拒绝且不回显 / AB=off 执行并回显。
          AB=on 臂: canary 出现次数必须 = 0 (红); 见证为 0 记 unreported (不冒充已收口)。
          AB=off 臂 (O1): canary 应出现 (正控); 出现 ⇒ 差分见证成立。
  T17     复述同义轮本地消化见证 (候选④): repeat_skip=on 时 t17 台账 kind=skip 且远端调用=0;
          repeat_skip=off (T1n 消融) 时 t17 应走远端 (≥1 调用) —— 单变量对照。

用法:
  python3 face_ext_r499.py --arm T1 --dir eval/rover/r499 --mount on --ab on --canary R499-OOB-CANARY-...
退出码: 0 = 面无红; 1 = 有红 (fail-closed); 3 = 输入缺失
"""
import argparse
import glob
import json
import os
import re
import sys

RAW_RX = re.compile(r"LCM-[0-9a-f]{12}")
FP8_RX = re.compile(r"^[0-9a-f]{8}$")
MOUNT_RX = re.compile(r"\[本地决策台账-链自持\][^\n]*code=(LCM-[0-9a-f]{12})")
T16_MARK = "r499oob"
T17_TXT = "从头念一遍"


def rjl(path):
    out = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for l in f:
                l = l.strip()
                if not l:
                    continue
                try:
                    out.append(json.loads(l))
                except Exception:
                    out.append({"_raw": l})
    except FileNotFoundError:
        return None
    return out


def rj(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return json.load(f)
    except Exception:
        return None


def walk_text(root, exts=(".json", ".jsonl", ".log", ".txt", ".md", ".csv")):
    if not os.path.isdir(root):
        return
    for dp, _dn, fn in os.walk(root):
        for n in fn:
            if n.endswith(exts):
                yield os.path.join(dp, n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--mount", choices=["on", "off"], required=True)
    ap.add_argument("--ab", choices=["on", "off"], required=True)
    ap.add_argument("--canary", required=True)
    a = ap.parse_args()
    D = a.dir.rstrip("/")
    arm = a.arm
    red, unreported, notes = [], [], []

    calls = rjl(os.path.join(D, "calls-%s.jsonl" % arm))
    turns = rj(os.path.join(D, "turns-%s.jsonl" % arm))
    if calls is None:
        print("[致命] 缺 calls-%s.jsonl" % arm)
        return 3
    flags = rj(os.path.join(D, "flags-%s.json" % arm)) or {}
    tel_path = os.path.join(D, "tel-%s/host.jsonl" % arm)
    tel = rjl(tel_path) or []
    ledger = rjl(os.path.join(D, "ledger-%s.jsonl" % arm)) or []
    rundata = os.path.join(D, "rundata-%s" % arm)

    # ---- 语料面: 实发 (wire) / 回显 (turns) / 打点 (tel) / 台账 (ledger) / 产品数据 (rundata)
    wire_txt = "\n".join(json.dumps(r, ensure_ascii=False) for r in calls)
    turn_txt = json.dumps(turns, ensure_ascii=False) if turns else ""
    tel_txt = "\n".join(json.dumps(r, ensure_ascii=False) for r in tel)
    led_txt = json.dumps(ledger, ensure_ascii=False)
    prod_files = list(walk_text(rundata)) + [os.path.join(D, "host-%s.log" % arm)]

    def scan_prod(pat):
        hits = []
        for p in prod_files:
            try:
                with open(p, encoding="utf-8", errors="replace") as f:
                    t = f.read()
            except Exception:
                continue
            n = t.count(pat) if isinstance(pat, str) else len(pat.findall(t))
            if n:
                hits.append({"file": os.path.relpath(p, D), "n": n})
        return hits

    # =============================================================== HARD-3b
    raw_in_tel = len(RAW_RX.findall(tel_txt))
    led_pts = [r for r in tel if isinstance(r, dict) and r.get("point") == "local_decision_ledger"]
    bad_kv = []
    for r in led_pts:
        kv = r.get("kv") or {}
        if "code" in kv:
            bad_kv.append("kv 仍带 raw code 键")
        if not FP8_RX.match(str(kv.get("code8", ""))):
            bad_kv.append("kv 缺 code8 指纹 (8 hex)")
        if not FP8_RX.match(str(kv.get("key_id", ""))):
            bad_kv.append("kv 缺 key_id 指纹 (8 hex)")
    codes_wire = sorted(set(MOUNT_RX.findall(wire_txt)))
    codes8_tel = sorted({str((r.get("kv") or {}).get("code8", "")) for r in led_pts} - {""})
    codes8_led = sorted({str(r.get("code8", "")) for r in ledger if isinstance(r, dict)} - {""})
    if raw_in_tel:
        red.append("HARD-3b: 打点面仍有 raw 码字面量 %d 处" % raw_in_tel)
    if bad_kv:
        red.append("HARD-3b: local_decision_ledger 点 kv 不合规: " + "; ".join(sorted(set(bad_kv))))
    if a.mount == "on" and codes_wire and not set(codes8_tel) <= set(codes8_led):
        red.append("HARD-3b: 打点指纹 %r 不在台账指纹集 %r 内 (跨面不一致)" % (codes8_tel, codes8_led))
    c3b = {"tel_rows": len(tel), "ledger_point_rows": len(led_pts), "raw_code_literals_in_tel": raw_in_tel,
           "kv_violations": sorted(set(bad_kv)), "wire_raw_codes": codes_wire, "tel_code8": codes8_tel,
           "ledger_code8": codes8_led, "mount": a.mount}

    # =============================================================== HARD-6
    tool_msgs, ref_file, ref_cmd = [], 0, 0
    t16_calls = 0
    for r in calls:
        for m in r.get("messages", []):
            if m.get("role") != "tool":
                continue
            c = m.get("content") or ""
            tool_msgs.append(c)
            if "路径越界" in c:
                ref_file += 1
            if "越界路径既不执行也不回显" in c or "rc=126" in c:
                ref_cmd += 1
    for r in calls:
        last_user = ""
        for m in r.get("messages", []):
            if m.get("role") == "user":
                last_user = m.get("content") or ""
        if T16_MARK in last_user:
            t16_calls += 1
    c_calls = wire_txt.count(a.canary)
    c_turns = turn_txt.count(a.canary)
    c_tel = tel_txt.count(a.canary)
    c_led = led_txt.count(a.canary)
    c_prod = scan_prod(a.canary)
    canary_total = c_calls + c_turns + c_tel + c_led + sum(h["n"] for h in c_prod)
    c6 = {"tool_msgs": len(tool_msgs), "refusal_file_face": ref_file, "refusal_cmd_face": ref_cmd,
          "calls_for_t16": t16_calls, "canary_in_wire": c_calls, "canary_in_turns": c_turns,
          "canary_in_tel": c_tel, "canary_in_ledger": c_led, "canary_in_product": c_prod,
          "canary_total": canary_total, "ab": a.ab}
    if a.ab == "on":
        if canary_total:
            red.append("HARD-6: AB=on 臂 canary 出现 %d 次 (越界正文进面)" % canary_total)
        if ref_file + ref_cmd == 0:
            unreported.append("候选③ 拒绝见证: 本臂工具面 0 条拒绝 (tool_msgs=%d) ⇒ 未测到" % len(tool_msgs))
        else:
            notes.append("候选③ 拒绝见证: 文件面 %d / 命令面 %d" % (ref_file, ref_cmd))
    else:
        if canary_total >= 1:
            notes.append("候选③ 正控 (AB=off): canary 出现在 %d 面 ⇒ 拒绝判定器有判别力" % canary_total)
        elif tool_msgs:
            unreported.append("候选③ 正控 (AB=off): 有 %d 条 tool 消息但 canary 未出现 ⇒ 正控未复现 (unreported)"
                              % len(tool_msgs))
        else:
            unreported.append("候选③ 正控 (AB=off): 工具面 0 条消息 ⇒ 未触发 (unreported)")

    # =============================================================== T17 (候选④)
    rs = str(flags.get("repeat_skip", ""))
    led17 = [r for r in ledger if str(r.get("turn")) == "17"]
    kind17 = led17[-1].get("kind") if led17 else None
    calls17 = 0
    for r in calls:
        last_user = ""
        for m in r.get("messages", []):
            if m.get("role") == "user":
                last_user = m.get("content") or ""
        if T17_TXT in last_user:
            calls17 += 1
    rep17, rep16 = None, None
    if turns and isinstance(turns.get("turns"), list):
        for t in turns["turns"]:
            if t.get("turn") == 17:
                rep17 = t.get("reply")
            if t.get("turn") == 16:
                rep16 = t.get("reply")
    replay_eq = (rep17 is not None and rep16 is not None and rep17.strip() == rep16.strip())
    c17 = {"repeat_skip": rs, "ledger_turn17_kind": kind17, "calls_for_t17": calls17,
           "t17_reply_equals_t16": replay_eq, "t17_reply_len": len(rep17 or ""),
           "t17_reply_head": (rep17 or "")[:60]}
    if rs == "on":
        if kind17 != "skip":
            red.append("候选④: repeat_skip=on 但 t17 台账 kind=%r (期望 skip)" % kind17)
        if calls17:
            red.append("候选④: repeat_skip=on 但 t17 仍走远端 (%d 次调用)" % calls17)
        if not replay_eq:
            unreported.append("候选④: t17 消化件 ≠ t16 答复 (replay 面未复现) ⇒ 本地消化形态待查")
    elif rs == "off":
        if kind17 == "skip" and calls17 == 0:
            red.append("候选④ 消融臂失效: repeat_skip=off 但 t17 仍被本地消化")
        if calls17 == 0 and kind17 is None:
            unreported.append("候选④ 消融臂: t17 无台账/无调用 (未测到)")
        notes.append("候选④ 消融臂 (repeat_skip=off): t17 kind=%r calls=%d" % (kind17, calls17))
    else:
        unreported.append("候选④: 本臂 repeat_skip=%r (非 on/off) ⇒ 该面 N/A" % rs)

    out = {"round": "R499", "instrument": "face_ext_r499.py", "arm": arm, "mount": a.mount, "ab": a.ab,
           "HARD-3b": c3b, "HARD-6": c6, "T17": c17, "red": red, "unreported": unreported, "notes": notes,
           "verdict": "GREEN" if not red else "RED"}
    with open(os.path.join(D, "face-ext-%s.json" % arm), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("[face_ext] arm=%s ab=%s mount=%s verdict=%s" % (arm, a.ab, a.mount, out["verdict"]))
    print("  HARD-3b: 打点 raw=%d 点行=%d kv违规=%s 线上面 raw 码=%d 打点指纹=%s"
          % (raw_in_tel, len(led_pts), c3b["kv_violations"], len(codes_wire), codes8_tel))
    print("  HARD-6: tool=%d 文件面拒绝=%d 命令面拒绝=%d t16调用=%d canary(wire/turns/tel/led/prod)=%d/%d/%d/%d/%d"
          % (len(tool_msgs), ref_file, ref_cmd, t16_calls, c_calls, c_turns, c_tel, c_led,
             sum(h["n"] for h in c_prod)))
    print("  T17   : repeat_skip=%s kind=%r calls=%d replay_eq=%s len=%d" % (rs, kind17, calls17, replay_eq, c17["t17_reply_len"]))
    for r in red:
        print("  [RED] " + r)
    for u in unreported:
        print("  [unreported] " + u)
    for n in notes:
        print("  [note] " + n)
    return 0 if not red else 1


if __name__ == "__main__":
    sys.exit(main())
