#!/usr/bin/env python3
"""R371 D7/D1 验收结算器 — **只取外部真值** (桩侧逐请求落盘 + 驱动器观测), 不信任被测量代码自报计数器。

判据 (预注册, 见 docs/plans/v0.22.0-r371-*.md §D7 验收):
  ok           : 0 个请求带恢复提示 ∧ 0 条 llm_call_continue/llm_call_recover  (负控: 无病不治)
  truncate     : 存在带 TruncatedNudge 的第二次请求 ∧ 遥测 llm_call_continue recovered=true ∧ after=before+added-overlap
                 ∧ 用户可见回复含续写独有片段 ∧ 合并结果结构闭合(独立复刻的纯语法判据)
  empty        : 存在带 NoReasoningNudge 的重试请求 ∧ 遥测 llm_call_recover recovered=true ∧ first_content_len=0 ∧ first_reasoning_len>0
  empty_always : 重试后仍空 => 遥测 recovered=false ∧ 用户可见回复=可见降级文案 ∧ 出参 success=False (不假装成功)

用法: python3 verdict.py [dir]
"""
import json
import os
import sys

D = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
TRUNC_TAIL_CHARS = "=([{,+-*/\\:"

# 独立复刻 (与产品实现同口径但独立编写; 用于"合并结果是否结构闭合"的外部判据)
def looks_truncated(s):
    if not s or not s.strip():
        return False
    t = s.rstrip()
    if not t:
        return False
    if t[-1] in TRUNC_TAIL_CHARS:
        return True
    n = 0
    i = t.find('"""')
    while i >= 0:
        n += 1
        i = t.find('"""', i + 3)
    if n % 2 == 1:
        return True
    return t.count("```") % 2 == 1


def load_jsonl(p):
    out = []
    if not os.path.exists(p):
        return out
    for line in open(p, encoding="utf-8"):
        line = line.strip().lstrip("\ufeff")
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


def tel_events(path, point):
    return [o["kv"] for o in load_jsonl(path) if o.get("point") == point]


def merge_continuation(head, tail):
    """独立复刻去重重拼 (与被测量代码无关的实现)。返回 (merged, overlap_len)。"""
    if not tail:
        return head, 0
    for ln in range(min(200, len(head), len(tail)), 5, -1):
        seg = head[len(head) - ln:]
        if seg == tail[:ln] and seg.strip():
            return head + tail[ln:], ln
    return head + tail, 0


def check_arm(arm):
    calls = load_jsonl(os.path.join(D, f"calls-{arm}.jsonl"))
    turns = json.load(open(os.path.join(D, f"turns-{arm}.jsonl"), encoding="utf-8"))["turns"] if os.path.exists(
        os.path.join(D, f"turns-{arm}.jsonl")) else []
    TEL = os.path.join(D, f"tel-{arm}.jsonl")
    cont = tel_events(TEL, "llm_call_continue")
    recov = tel_events(TEL, "llm_call_recover")
    lcalls = tel_events(TEL, "llm_call")
    trunc_flag = [c for c in lcalls if c.get("truncated") is True]
    replies = "\n".join((t.get("reply") or "") for t in turns)
    c = {}
    if arm == "ok":
        c["1 无恢复提示请求"] = (len([x for x in calls if x.get("nudge_trunc") or x.get("nudge_noreason")]) == 0,
                              f"{len(calls)} 请求 / 0 带提示")
        c["2 无恢复遥测"] = (len(cont) == 0 and len(recov) == 0, f"continue={len(cont)} recover={len(recov)}")
        c["3 无截断标记"] = (len(trunc_flag) == 0, f"truncated=true {len(trunc_flag)} 条")
        c["4 回复非空"] = (len(replies.strip()) > 0, f"reply_chars={len(replies)}")
    elif arm == "truncate":
        nudge = [x for x in calls if x.get("nudge_trunc")]
        c["1 存在续写请求(带断点提示)"] = (len(nudge) >= 1, f"{len(nudge)} 条带 TruncatedNudge (共 {len(calls)} 请求)")
        ok_cont = [x for x in cont if x.get("recovered") is True]
        c["2 遥测 llm_call_continue recovered=true"] = (len(ok_cont) >= 1, json.dumps(ok_cont[:1], ensure_ascii=False)[:200])
        # 独立复刻: 取"带 nudge 的那次请求"(续写) 与其前一次(截断) 的**桩侧应答原文**重算合并
        exp_len, exp_overlap, head_len, retry_raw_len, prev_raw = -1, -1, -1, -1, ""
        if nudge:
            retry = nudge[0]
            prev = [x for x in calls if x["seq"] == retry["seq"] - 1]
            if prev:
                head, tail = prev[0].get("resp_content") or "", retry.get("resp_content") or ""
                merged, exp_overlap = merge_continuation(head, tail)
                exp_len, head_len = len(merged), len(head)
                retry_raw_len, prev_raw = len(tail), head
        if ok_cont:
            k = ok_cont[0]
            c["3 after_len=独立复刻合并长度"] = (int(k.get("after_len") or -1) == exp_len,
                                          f"代码自报 after={k.get('after_len')} / 独立复刻 {exp_len}(overlap={exp_overlap})")
            c["4 before_len=桩侧截断正文长"] = (int(k.get("before_len") or -1) == head_len,
                                         f"before={k.get('before_len')} / 桩侧 {head_len}")
            c["5 added_len=续写原文长度(去重前)"] = (
                int(k.get("added_len") or -1) == retry_raw_len,
                f"added={k.get('added_len')} / 桩侧续写原文 {retry_raw_len}")
            c["6 tail_before=桩侧截断尾部"] = (
                (k.get("tail_before") or "") == (prev_raw[-len(k.get("tail_before") or "\x00"):] if k.get("tail_before") else "\x00"),
                f"tail_before={k.get('tail_before')!r}")
        # 口径说明: llm_call.truncated 记录的是**最终**正文的结构闭合性 => 救回后应为 false;
        # 「首轮确实被截断」这一事实由 llm_call_continue.before_len/tail_before 携带。
        c["7 救回后 truncated=false(口径: 反映最终正文)"] = (len(trunc_flag) == 0,
                                                  f"truncated=true {len(trunc_flag)} 条 / 断点事实见 continue 事件")
        c["8 用户可见回复含续写独有片段"] = ("return acc" in replies, "含 'return acc'")
        c["9 合并结果结构闭合(独立纯语法判据)"] = (
            (not looks_truncated(replies.strip())) and len(replies.strip()) > 0,
            f"可见回复尾部={replies.strip()[-14:]!r}")
    elif arm == "empty":
        nudge = [x for x in calls if x.get("nudge_noreason")]
        c["1 存在抑制推理重试请求"] = (len(nudge) >= 1, f"{len(nudge)} 条带 NoReasoningNudge")
        ok_rec = [x for x in recov if x.get("recovered") is True]
        c["2 遥测 llm_call_recover recovered=true"] = (len(ok_rec) >= 1, json.dumps(ok_rec[:1], ensure_ascii=False))
        if ok_rec:
            k = ok_rec[0]
            _fc = k.get("first_content_len")
            c["3 first_content_len=0 且 first_reasoning_len>0"] = (
                (_fc is not None and int(_fc) == 0) and int(k.get("first_reasoning_len") or 0) > 0,
                f"first_content={k.get('first_content_len')} first_reasoning={k.get('first_reasoning_len')}")
        c["4 回复为正文(非空)"] = (len(replies.strip()) > 0 and "模型未产出正文" not in replies,
                             f"reply_chars={len(replies)}")
        c["5 首轮 reasoning 非空已被识别"] = (any(int(x.get("resp_reasoning_len") or 0) > 0 for x in calls),
                                       "桩侧首轮带 reasoning")
    elif arm == "empty_always":
        nudge = [x for x in calls if x.get("nudge_noreason")]
        c["1 存在抑制推理重试请求"] = (len(nudge) >= 1, f"{len(nudge)} 条带 NoReasoningNudge")
        bad = [x for x in recov if x.get("recovered") is False]
        c["2 遥测 recovered=false (如实不救回)"] = (len(bad) >= 1, f"{len(bad)} 条")
        c["3 回复=可见降级文案"] = ("模型未产出正文" in replies, f"命中={('模型未产出正文' in replies)}")
        c["4 success=False (不假装成功)"] = (any(t.get("success") is False for t in turns),
                                        f"success={[t.get('success') for t in turns]}")
        # R414 修复判据: 失败轮喂给用户的回复必须**有可见文案** (修复前: 轮 1 reply_len=0, 用户看到空白)
        lens = [len(t.get("reply") or "") for t in turns]
        c["5 修复后失败轮可见文案非空(每轮)"] = (all(x > 0 for x in lens), f"reply_len={lens}")
        bf = os.path.join(D, "turns-before-fix-empty_always.jsonl")
        if os.path.exists(bf):
            with open(bf, encoding="utf-8") as fh:
                bt = (json.load(fh).get("turns") or [])
            bl = [len(t.get("reply") or "") for t in bt]
            c["6 修复前对照=有轮次为空白(证明变化来自修复)"] = (any(x == 0 for x in bl), f"修复前 reply_len={bl}")
    else:
        raise SystemExit("unknown arm " + arm)
    return {"arm": arm, "requests": len(calls), "checks": {k: {"pass": bool(v[0]), "detail": v[1]} for k, v in c.items()}}


def check_aot_form():
    """AOT 发布形态复跑 (run_arm.sh 第 4 参 = aot): 修复与 D7 必须在**发布形态**上成立。"""
    checks = {}
    for arm, want_len, want_succ in (("empty_always", [66, 73], [False, False]),
                                     ("truncate", [144, 151], [True, True])):
        tp = os.path.join(D, "turns-%s-aot.jsonl" % arm)
        cp = os.path.join(D, "calls-%s-aot.jsonl" % arm)
        if not (os.path.exists(tp) and os.path.exists(cp)):
            checks[arm] = (False, "缺 AOT 形态证据文件")
            continue
        with open(tp, encoding="utf-8") as fh:
            turns = (json.load(fh).get("turns") or [])
        with open(cp, encoding="utf-8") as fh:
            calls = [json.loads(l) for l in fh if l.strip()]
        ln = [len(t.get("reply") or "") for t in turns]
        su = [t.get("success") for t in turns]
        checks[arm + " 可见回复/成功位"] = (ln == want_len and su == want_succ, "reply_len=%s success=%s" % (ln, su))
        if arm == "truncate":
            n = sum(1 for r in calls if r.get("nudge_trunc"))
            checks[arm + " 续写调用(外部真值)"] = (n >= 1 and len(calls) > 2, "请求=%d 带断点提示=%d" % (len(calls), n))
        else:
            n = sum(1 for r in calls if r.get("nudge_noreason"))
            checks[arm + " 抑制推理重试(外部真值)"] = (n >= 1, "请求=%d 带抑制提示=%d" % (len(calls), n))
    return {"arm": "AOT-form", "requests": None,
            "checks": {k: {"pass": bool(v[0]), "detail": v[1]} for k, v in checks.items()}}


def main():
    arms = ["ok", "truncate", "empty", "empty_always"]
    res = [check_arm(a) for a in arms] + [check_aot_form()]
    allpass = all(x["pass"] for r in res for x in r["checks"].values())
    out = {"verdict": "PASS" if allpass else "FAIL", "arms": res}
    p = os.path.join(D, "verdict-r371d7.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    for r in res:
        print(f"=== {r['arm']} (远端请求 {r['requests']}) ===")
        for k, v in r["checks"].items():
            print(("  PASS  " if v["pass"] else "  FAIL  ") + k + " | " + str(v["detail"])[:150])
    print("VERDICT=" + out["verdict"], "->", p)


if __name__ == "__main__":
    main()
