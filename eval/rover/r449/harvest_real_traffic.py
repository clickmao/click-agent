#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R449 · 通道 A0: 用户↔agent 真实对话收割 (外部真值语料).

用户钦定: 「我给你发任务, 你给我反馈, 这个过程本就是真实流量」
⇒ 外部真值通道 A0 = Hermes 会话库 (state.db) 里的真实 (用户消息, 上一条助手反馈) 对,
   标签 = 用户**下一条**消息的性质 (采纳 / 纠正 / 换题) —— 系统外、非我构造、非归档代理。

只读; 不改库; 输出:
  eval/rover/r449/real-corpus.jsonl   逐条语料(含 prev 反馈截 160 字 == 判官输入面)
  eval/rover/r449/real-traffic-census.json  机检读数
纪律: 规则标签 (可复算) + 每类给样例; 不宣称这是精确标签, 只作外部一致性分母。
"""
import collections
import json
import pathlib
import re
import sqlite3
import sys

DB = "file:/home/agentuser/.hermes/state.db?mode=ro"
ROOT = pathlib.Path("/home/agentuser/AgentFramework")
OUTDIR = ROOT / "eval/rover/r449"

INJECT = [
    r"^\s*\[Cron delivery", r"CONTEXT COMPACTION", r"## Historical Task Snapshot",
    r"\[OUT-OF-BAND USER MESSAGE", r"^\s*## 第 \d+ 步", r"^\s*Work complete\. Final report",
    r"^\s*\[Reminder\]", r"^\s*<system", r"^\s*SYSTEM:",
]
INJECT_RE = re.compile("|".join(INJECT), re.I)

ADOPT = ["好，按这个来", "好,按这个来", "就这样", "可以了", "收到", "谢谢", "继续", "对的", "没错",
         "就这么办", "按你说的", "ok", "OK", "👍", "辛苦了", "可以，继续", "好"]
CORRECT = ["不对", "不是这样", "错了", "有问题", "重新", "改成", "修正", "失败", "没生效", "没实现",
           "不成立", "为什么", "为啥", "何意味", "依据是什么", "存疑", "偏离", "注意", "但是", "但"]


def classify(msg: str) -> str:
    s = msg.strip()
    low = s.lower()
    if any(k in s for k in CORRECT) or re.search(r"(不对|不是|没(有)?(生效|实现|看到|执行)|重(新|做)|修(改|正))", s):
        return "correct"
    if len(s) <= 40 and (any(k in s for k in ADOPT) or low in ("ok", "okay", "yes", "y", "+1")):
        return "adopt"
    return "new_task"


def main():
    con = sqlite3.connect(DB, uri=True)
    rows = list(con.execute(
        "select session_id, id, role, content, timestamp from messages "
        "where role in ('user','assistant') order by session_id, id"))
    n_user = sum(1 for r in rows if r[2] == "user")
    n_asst = sum(1 for r in rows if r[2] == "assistant")

    per = collections.defaultdict(list)
    for sid, mid, role, content, ts in rows:
        per[sid].append((mid, role, content or "", ts))

    corpus, excl = [], 0
    for sid, seq in per.items():
        prev_asst = None
        for mid, role, content, ts in seq:
            if role == "assistant":
                prev_asst = content
                continue
            if INJECT_RE.search(content[:200]):
                excl += 1
                continue
            if len(content.strip()) == 0:
                excl += 1
                continue
            corpus.append({
                "session": sid, "mid": mid, "ts": ts,
                "user_msg": content,
                "user_len": len(content),
                "prev_reply": (prev_asst or "")[:160],
                "label": classify(content),
            })

    lab = collections.Counter(c["label"] for c in corpus)
    lens = [c["user_len"] for c in corpus]
    buckets = collections.Counter(
        "<=10" if x <= 10 else "11-40" if x <= 40 else "41-120" if x <= 120
        else "121-400" if x <= 400 else ">400" for x in lens)
    with_reply = sum(1 for c in corpus if c["prev_reply"])
    lab_wr = collections.Counter(c["label"] for c in corpus if c["prev_reply"])

    # 网格代表性对照
    grid = {}
    for gp in [ROOT / "eval/rover/r446/grid/task-M20.json", ROOT / "eval/rover/r444/grid/task-M20.json"]:
        if gp.exists():
            try:
                d = json.loads(gp.read_text(encoding="utf-8"))
                ts = d if isinstance(d, list) else (d.get("turns") or d.get("messages") or [])
                msgs = [t.get("msg") or t.get("message") or t.get("user") or "" for t in ts if isinstance(t, dict)]
                msgs = [m for m in msgs if m]
                grid[gp.name + "@" + gp.parent.parent.name] = {
                    "n": len(msgs), "lens": sorted(len(m) for m in msgs),
                    "buckets": dict(collections.Counter(
                        "<=10" if len(m) <= 10 else "11-40" if len(m) <= 40 else "41-120" if len(m) <= 120
                        else ">400" for m in msgs))}
            except Exception as e:
                grid[gp.name] = {"err": str(e)}
            break

    OUTDIR.mkdir(parents=True, exist_ok=True)
    with open(OUTDIR / "real-corpus.jsonl", "w", encoding="utf-8") as f:
        for c in corpus:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    doc = {
        "round": "R449", "channel": "A0 用户↔agent 真实对话",
        "db": DB.split("?")[0], "sessions": len(per),
        "messages_user": n_user, "messages_assistant": n_asst,
        "excluded_injected": excl, "real_user_turns": len(corpus),
        "with_prev_reply": with_reply,
        "label_all": dict(lab), "label_with_prev_reply": dict(lab_wr),
        "len_buckets": dict(buckets),
        "len_min_med_max": [min(lens), sorted(lens)[len(lens) // 2], max(lens)] if lens else None,
        "grid_reference": grid,
        "classifier": {"correct_kw": CORRECT, "adopt_kw": ADOPT, "note": "规则标签, 可复算; 噪声已知, 只作外部一致性分母"},
        "verdict": "CHANNEL_A0_AVAILABLE" if len(corpus) >= 100 and with_reply >= 100 else "SAMPLE_TOO_SMALL",
    }
    (OUTDIR / "real-traffic-census.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"真实用户轮 = {len(corpus)} (排除注入/空 = {excl}) | 有上一条助手反馈 = {with_reply}")
    print(f"标签(全) = {dict(lab)}")
    print(f"标签(有反馈) = {dict(lab_wr)}")
    print(f"长度分桶 = {dict(buckets)} | min/med/max = {doc['len_min_med_max']}")
    print(f"网格对照 = {grid}")
    print(f"[结论] {doc['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
