#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R468 外部效度器具: 真实流量（用户↔agent 对话）上按**产品门判规则**分类。

数据源: ~/.hermes/state.db (只读) — messages.role='user' 的真实用户轮。
规则源: gate_rules.py (源码派生 + 产品测试期望值自检) —— **不使用任何自造语义**。
口径（用户令 R449: "有效性得筛选，因为大部分时候我的回复仅是让你执行下一轮"）:
  · 系统注入 (cron/压缩/OOB/后台完成通知) 一律剔除，不计入任何分母;
  · 驱动类 (继续/下一步/进行下轮…) **单列**，既不算采纳标签也不算可跳面（产品判它们为 pass = 保守走远端）。
输出: eval/rover/r468/real-traffic.json + real-traffic-corpus.jsonl (供 C# 差分校验)
用法: python3 real_traffic_classify.py [--db PATH] [--sample N]
"""
import argparse, io, json, os, re, sqlite3, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gate_rules as G  # noqa: E402

INJECT_PREFIX = ("[Cron delivery", "[IMPORTANT", "[CONTEXT COMPACTION", "[OUT-OF-BAND",
                 "## Historical", "<system", "[System", "[Reminder", "[Notification",
                 "MEDIA:", "[Tool", "[ERROR")
DRIVER_PAT = re.compile(r"^(继续|继续下|继续做|继续推进|继续优化|继续任务|持续优化|持续|下一步|进行下轮|进行下一轮|"
                        r"进行下一步|下轮|下一轮|接着|go on|next)[。.!！\s]*$")
GRID = ["把构建命令写成一行。", "谢谢，收到。", "好的，明白。", "嗯嗯，知道了。", "明白，多谢。", "再讲一遍。",
        "讲细一点。", "换个说法。", "从头再说。", "你上一条说 3 加 5 等于 9，对吧？", "讲详细些。", "你上一条说的那个。"]


def genuine(msg):
    if not msg:
        return False
    m = msg.strip()
    if not m or m.startswith(INJECT_PREFIX):
        return False
    if "background process" in m and "completed" in m:
        return False
    if m.startswith("{") or m.startswith("```"):
        return False
    return True


def _counts(rows):
    st = collections.Counter()
    for _sid, content, _ts in rows:
        if not genuine(content):
            st["injected_or_system"] += 1
            continue
        st["genuine_user_turns"] += 1
        c = G.classify(content)
        st["driver" if (DRIVER_PAT.match(content.strip()) and len(content.strip()) <= 30) else c] += 1
    return dict(st)


NC_INJECT = ["\u597d\u7684\uff0c\u660e\u767d\u3002", "\u518d\u8bb2\u4e00\u904d\u3002"]


def neg_control():
    """\u8d1f\u63a7: \u5411\u771f\u5b9e\u8bed\u6599\u6ce8\u5165\u53ef\u8df3\u884c \u21d2 \u53ef\u8df3\u9762\u5fc5\u987b\u53d8\u975e 0\u3002
    \u82e5\u6307\u6807\u6052 0 (\u786c\u7f16\u7801/\u7a7a\u5fc3) \u5219\u6b64\u8d1f\u63a7\u4e0d\u4f1a\u53d8\u5316 \u21d2 \u5224\u7ea2\u3002"""
    labels = [G.classify(t) for t in NC_INJECT]
    skip = sum(1 for c in labels if c in ("ack", "repeat"))
    out = {"neg_control": True, "injected": NC_INJECT, "labels": labels,
           "skip_face": skip, "verdict": "PASS" if skip == 2 else "FAIL"}
    io.open(os.path.join(HERE, "neg-control-r468.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False))
    return 0 if skip == 2 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.path.expanduser("~/.hermes/state.db"))
    ap.add_argument("--sample", type=int, default=400)
    ap.add_argument("--neg-control", action="store_true")
    a = ap.parse_args()
    if a.neg_control:
        return neg_control()
    con = sqlite3.connect("file:%s?mode=ro" % a.db, uri=True)
    rows = list(con.execute(
        "select session_id, content, timestamp from messages "
        "where role='user' and content is not null and content<>'' order by timestamp"))
    active_rows = list(con.execute(
        "select session_id, content, timestamp from messages "
        "where role='user' and content is not null and content<>'' and active=1 order by timestamp"))
    stat = collections.Counter()
    per_session = collections.defaultdict(collections.Counter)
    corpus, lens = [], collections.Counter()
    drivers = []
    for sid, content, ts in rows:
        if not genuine(content):
            stat["injected_or_system"] += 1
            continue
        stat["genuine_user_turns"] += 1
        c = G.classify(content)
        is_driver = bool(DRIVER_PAT.match(content.strip())) and len(content.strip()) <= 30
        key = "driver" if is_driver else c
        stat[key] += 1
        per_session[sid][key] += 1
        lens[min(len(content.strip()) // 10 * 10, 200)] += 1
        if is_driver:
            drivers.append(content.strip()[:40])
        if len(corpus) < a.sample:
            corpus.append({"text": content.strip()[:300], "class": c, "driver": is_driver})
    n = stat["genuine_user_turns"] or 1
    grid = collections.Counter()
    for t in GRID:
        c = G.classify(t)
        grid["driver" if DRIVER_PAT.match(t) else c] += 1
    skipface = stat["ack"] + stat["repeat"]
    sessions_with = len([s for s, v in per_session.items() if v["ack"] + v["repeat"] > 0])
    out = {
        "source": a.db,
        "rules_meta": G.RULES_META,
        "counts": dict(stat),
        "genuine_user_turns": stat["genuine_user_turns"],
        "skip_face": {"ack": stat["ack"], "repeat": stat["repeat"], "total": skipface,
                      "share": round(skipface / n, 4)},
        "driver_share": round(stat["driver"] / n, 4),
        "pass_share": round(stat["pass"] / n, 4),
        "other_share": round(stat["other"] / n, 4),
        "sessions_total": len(per_session),
        "sessions_with_skip_face": sessions_with,
        "len_hist_bucket": {str(k): v for k, v in sorted(lens.items())},
        "driver_examples": drivers[:20],
        "grid_p12": dict(grid),
        "active_only_counts": _counts(active_rows),
        "sql_scope": "all user rows (active 不限); active_only_* 为仅 active=1 子集",
    }
    io.open(os.path.join(HERE, "real-traffic.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    # 差分语料 = 真实轮 + 网格 p12 + 产品测试 InlineData 用例族 (高信号覆盖, 供 C# 差分校验)
    seen = {r["text"] for r in corpus}
    for t in GRID:
        if t not in seen:
            corpus.append({"text": t, "class": G.classify(t), "driver": False, "src": "grid_p12"})
            seen.add(t)
    for meth, fn in (("G31_认可族结构确认", G.mechanical_ack), ("G35_纯复述族结构确认", G.is_pure_repeat)):
        for msg, _exp in G._inline_cases(G._test_src, meth):
            if msg not in seen:
                corpus.append({"text": msg, "class": G.classify(msg), "driver": False, "src": "test_inlinedata"})
                seen.add(msg)
    with io.open(os.path.join(HERE, "real-traffic-corpus.jsonl"), "w", encoding="utf-8") as f:
        for r in corpus:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    out["corpus_rows"] = len(corpus)
    io.open(os.path.join(HERE, "real-traffic.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "len_hist_bucket"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
