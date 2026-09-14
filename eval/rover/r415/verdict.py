#!/usr/bin/env python3
"""R415 判定器 — 链级「门入参 = 用户原文」钉死。

判据先于测量 (见 README-evidence.md §判据), 全部取**外部真值**:
  calls-*.jsonl     = 远端桩逐请求落盘 (OpenAI 兼容请求体)
  llamareq-*.jsonl  = 假本地后端逐请求落盘 (llama-server 兼容请求体)
被测量代码自报的遥测一律不作判据来源。

用法: python3 verdict.py [aot]   # 传 aot 时并判 AOT 形态复跑 (-aot 后缀)
"""
import json
import os
import sys

D = os.path.dirname(os.path.abspath(__file__))
SENTINEL = "SENTINEL_SKILL_7F3A"
REF_BLOCK = "[本轮参考上下文]"
SKILL_BLOCK = "[技能知识参考]"
GREET = "收到，谢谢。"
P_TURN = "嗯，就这样。"

checks = []


def add(name, ok, detail):
    checks.append({"id": name, "pass": bool(ok), "detail": detail})


def rows(path):
    out = []
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def load_turns(path):
    """turns-*.jsonl 实为 indent=2 的整个 JSON 对象 (drive_task.py 写盘) ⇒ 整体解析。"""
    if not os.path.exists(path):
        return []
    try:
        return json.load(open(path, encoding="utf-8")).get("turns", [])
    except Exception:
        return []


def flat(msgs):
    parts = []
    for m in msgs or []:
        c = m.get("content")
        if isinstance(c, str):
            parts.append(c)
        elif isinstance(c, list):
            for p in c:
                if isinstance(p, dict) and isinstance(p.get("text"), str):
                    parts.append(p["text"])
    return "\n".join(parts)


def last_user(msgs):
    for m in reversed(msgs or []):
        if (m.get("role") or "") == "user":
            c = m.get("content")
            if isinstance(c, str):
                return c
            if isinstance(c, list):
                return "".join(p.get("text", "") for p in c if isinstance(p, dict))
    return ""


def analyze(tag):
    """tag = 后缀 ('', '-aot')。返回 (calls, llama) 行表。"""
    calls = rows(os.path.join(D, f"calls-pin{tag}.jsonl"))
    llama = rows(os.path.join(D, f"llamareq-pin{tag}.jsonl"))
    turns = load_turns(os.path.join(D, f"turns-pin{tag}.jsonl"))
    off_calls = rows(os.path.join(D, f"calls-off{tag}.jsonl"))
    off_llama_path = os.path.join(D, f"llamareq-off{tag}.jsonl")
    off_llama = rows(off_llama_path)
    lab = "pin" if not tag else "pin(aot)"

    at = [r for r in llama if r.get("t") == "apply-template"]
    at_text = "\n".join(flat(r.get("messages")) for r in at)
    add(f"A1 [{lab}] 门确实问了本地判定器 (apply-template 请求 >= 1)",
        len(at) >= 1, f"apply-template={len(at)}")
    add(f"A2 [{lab}] 判别请求逐字含用户本轮原文",
        GREET in at_text, f"含原文={GREET in at_text} judge文本长={len(at_text)}")
    add(f"A3 [{lab}] ★判别力核心: 判别请求不含本哨兵 (门吃 message.Content 而非 prompt.UserMessage)",
        SENTINEL not in at_text, f"哨兵命中={at_text.count(SENTINEL)}")
    add(f"A4 [{lab}] 判别请求不含 [本轮参考上下文]/[技能知识参考] 块",
        (REF_BLOCK not in at_text) and (SKILL_BLOCK not in at_text),
        f"参考块={at_text.count(REF_BLOCK)} 技能块={at_text.count(SKILL_BLOCK)}")

    greet_remote = sum(1 for r in calls if last_user(r.get("messages")).strip().startswith(GREET))
    p_remote = sum(1 for r in calls if last_user(r.get("messages")).strip().startswith(P_TURN))
    calls_text = "\n".join(flat(r.get("messages")) for r in calls)
    add(f"A5 [{lab}] S 轮被跳过: 远端无「末条 user = 寒暄」的请求",
        greet_remote == 0, f"命中={greet_remote} 远端调用总数={len(calls)}")
    add(f"A6 [{lab}] 假阴性=0: P 轮未被跳过 (远端确有该轮请求)",
        p_remote >= 1, f"命中={p_remote}")
    add(f"A7 [{lab}] 正控·判别力自证: 远端请求里确实出现哨兵 + 参考块",
        (SENTINEL in calls_text) and (REF_BLOCK in calls_text),
        f"哨兵={calls_text.count(SENTINEL)} 参考块={calls_text.count(REF_BLOCK)}")
    canned = "桩应答"
    skip_reply = (turns[0].get("reply") or "") if turns else ""
    p_reply = (turns[1].get("reply") or "") if len(turns) > 1 else ""
    add(f"A10 [{lab}] 跳过轮回复不来自远端桩 (可见文案来自本地模板)",
        bool(skip_reply) and canned not in skip_reply, f"t1回复={skip_reply[:24]!r}")
    add(f"A11 [{lab}] 正控: P 轮回复确实来自远端桩",
        canned in p_reply, f"t2回复={p_reply[:24]!r}")
    nonempty = all(bool((t.get("reply") or "").strip()) for t in turns)
    add(f"A8 [{lab}] 跳过轮不静默: 每轮都有可见回复",
        bool(turns) and nonempty, f"轮数={len(turns)} reply非空={nonempty}")
    add(f"A9 [{lab}] 负控(本地通道关): 同一轮本就会走远端, 且假后端从未启动",
        greet_remote_off == 1 and len(off_llama) == 0,
        f"off远端命中={greet_remote_off} off本地请求={len(off_llama)}")

    return calls, llama


if __name__ == "__main__":
    # 负控臂统一在 analyze 前置算好, 这里预取
    off_path = os.path.join(D, "calls-off.jsonl")
    _off = rows(off_path)
    greet_remote_off = sum(1 for r in _off if last_user(r.get("messages")).strip().startswith(GREET))
    analyze("")
    if len(sys.argv) > 1 and sys.argv[1] == "aot":
        off_llama = rows(os.path.join(D, "llamareq-off-aot.jsonl"))
        greet_remote_off = sum(1 for r in rows(os.path.join(D, "calls-off-aot.jsonl"))
                               if last_user(r.get("messages")).strip().startswith(GREET))
        analyze("-aot")

    failed = [c for c in checks if not c["pass"]]
    verdict = "PASS" if not failed else "FAIL"
    report = {"verdict": verdict, "total": len(checks), "failed": len(failed),
              "criteria_pre_registered_in": "eval/rover/r415/README-evidence.md",
              "checks": checks}
    with open(os.path.join(D, "verdict-r415.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    for c in checks:
        print(("  OK  " if c["pass"] else "  FAIL") + f" {c['id']} | {c['detail']}")
    print(f"\nVERDICT={verdict} 断言 {len(checks) - len(failed)}/{len(checks)} 通过")
