#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R449 · 通道 A0 筛选与外部效度检验 (用户 OOB 钦定: 「有效性得筛选」).

用户原话: 「但是有效性得筛选, 因为大部分时候我的回复仅是让你执行下一轮」
⇒ 语料分三类, **先定规则再看数**(规则即预注册, 写在脚本里):
   D 迭代驱动: 只是驱动千轮循环(继续/下一轮/开下轮/不用问…), **不作采纳/纠正标签**
   O 运维质询: 涉及部署面(lightvela/console/api/dns/证书/服务端), 单列通道
   S 实质反馈: 任务指令/设计裁定/纠错 —— **只有 S 带外部真值标签**

再做外部效度: 用 R444 机械门的**源码派生**规则(Ack 字符表从 .cs 现场正则提取并断言)
量真实流量上「潜在可跳轮占比」, 与合成网格 M20 (7/20 = 35%) 对账。
只读; 输出 eval/rover/r449/external-validity-gate.json。
"""
import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
SRC = ROOT / "src/agent.modelqueue/LocalGenerationPort.cs"
CORPUS = ROOT / "eval/rover/r449/real-corpus.jsonl"
OUT = ROOT / "eval/rover/r449/external-validity-gate.json"
GRID = ROOT / "eval/rover/r446/grid/task-M20.json"

# --- 预注册筛选规则 (先于读数) ---
DRIVE_RE = re.compile(r"(继续|下一轮|下轮|开下?一轮|进行下|接着下|不用问|照做|执行吧|按计划|go on|next round|"
                      r"继续跑|往下|推进|不等|自动下一轮|30m|60m)")
OPS_RE = re.compile(r"(lightvela|lightclaw|console|api\.|dns|证书|域名|部署|线上|服务端|nginx|http|端点|运维)", re.I)
CORRECT_RE = re.compile(r"(不对|不是|错了|有问题|存疑|为什么|为啥|何意味|依据|失败|没(有)?(生效|实现|看到|出现)|"
                        r"漏|缺|偏离|注意|但是|重新|修正|改成|不成立)")
ADOPT_RE = re.compile(r"^(好|行|可以|嗯|收到|谢谢|OK|ok|对)[，,。!！~ ]*$")


def load_ack_family():
    """忠实性闸: Ack 字符表从源码现场派生, 与本地常量比对."""
    txt = SRC.read_text(encoding="utf-8")
    m = re.search(r'AckFamilyChars\s*=\s*"([^"]+)"', txt)
    if not m:
        print("[fail-closed] 源码未找到 AckFamilyChars")
        sys.exit(2)
    return m.group(1)


def load_signals():
    txt = SRC.read_text(encoding="utf-8")
    out = {}
    for name in ("QuestionSignals", "RequestSignals", "CorrectionSignals"):
        m = re.search(name + r"\s*=\s*\{(.*?)\};", txt, re.S)
        if not m:
            print(f"[fail-closed] 源码未找到 {name}")
            sys.exit(2)
        out[name] = re.findall(r'"([^"]+)"', m.group(1))
    return out


def mechanical_ack(msg, ack_chars):
    m = (msg or "").strip()
    if not m:
        return False
    n = 0
    for ch in m:
        if ch.isspace() or (not ch.isalnum()):
            continue
        if ch not in ack_chars:
            return False
        n += 1
        if n > 10:
            return False
    return n > 0


def mechanical_pass(msg, sig):
    if not (msg or "").strip():
        return True
    m = msg.strip()
    if "?" in m or "？" in m:
        return True
    for arr in ("QuestionSignals", "RequestSignals", "CorrectionSignals"):
        for w in sig[arr]:
            if w in m:
                return True
    if "`" in m or "/" in m or "\\" in m:
        return True
    if any(c.isdigit() for c in m):
        return True
    return len(m) >= 24


def main():
    ack_chars = load_ack_family()
    sig = load_signals()
    assert "好" in ack_chars and "的" in ack_chars, "Ack 字符表派生异常"
    rows = [json.loads(l) for l in CORPUS.read_text(encoding="utf-8").splitlines() if l.strip()]

    klass = collections.Counter()
    for r in rows:
        msg = r["user_msg"]
        r["klass"] = "D" if DRIVE_RE.search(msg[:60]) else ("O" if OPS_RE.search(msg[:200]) else "S")
        klass[r["klass"]] += 1

    def stat(sub):
        n = len(sub)
        if not n:
            return {"n": 0}
        ack = sum(1 for r in sub if mechanical_ack(r["user_msg"], ack_chars))
        pas = sum(1 for r in sub if mechanical_pass(r["user_msg"], sig))
        elig = [r for r in sub if mechanical_ack(r["user_msg"], ack_chars) and not mechanical_pass(r["user_msg"], sig)]
        lab = collections.Counter(r["label"] for r in sub)
        lab_e = collections.Counter(r["label"] for r in elig)
        return {
            "n": n, "ack": ack, "ack_pct": round(100 * ack / n, 1),
            "mech_pass": pas, "mech_pass_pct": round(100 * pas / n, 1),
            "gate_eligible": len(elig), "gate_eligible_pct": round(100 * len(elig) / n, 1),
            "label": dict(lab), "label_gate_eligible": dict(lab_e),
            "elig_examples": [r["user_msg"][:40] for r in elig[:5]],
        }

    classes = {k: [r for r in rows if r["klass"] == k] for k in ("S", "D", "O")}
    res = {k: stat(v) for k, v in classes.items()}
    res["ALL"] = stat(rows)

    grid_note = None
    if GRID.exists():
        g = json.loads(GRID.read_text(encoding="utf-8"))
        gt = g.get("turns") or []
        gi = sum(1 for t in gt if mechanical_ack(t, ack_chars) and not mechanical_pass(t, sig))
        grid_note = {"grid_turns": len(gt), "gate_eligible": gi,
                     "declared_ratio": g.get("ratio"),
                     "gate_eligible_pct": round(100 * gi / len(gt), 1) if gt else None}

    doc = {"round": "R449", "corpus": str(CORPUS), "prereg_rules": {
        "D_drive": DRIVE_RE.pattern, "O_ops": OPS_RE.pattern,
        "S_substantive": "其余全部", "ack_chars_derived": ack_chars,
        "note": "规则先落盘(本脚本)后读数; D 类不作采纳/纠正标签"},
        "class_counts": dict(klass), "stats": res, "grid_M20": grid_note,
        "verdict_by_class": {k: ("带真值标签" if k == "S" else "不作标签") for k in ("S", "D", "O")}}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    for k in ("ALL", "S", "D", "O"):
        s = res[k]
        print(f"[{k}] n={s['n']} ack={s.get('ack_pct')}% mechPass={s.get('mech_pass_pct')}% "
              f"可跳轮(gate_eligible)={s.get('gate_eligible')}({s.get('gate_eligible_pct')}%) label={s.get('label')}")
    print("S 类可跳轮标签:", res["S"].get("label_gate_eligible"), "| 样例:", res["S"].get("elig_examples"))
    print("网格 M20:", grid_note)
    print(f"[out] {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
