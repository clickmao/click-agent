#!/usr/bin/env python3
"""R452 turn 构建器 — 真实语料按**会话序**拼成产品原生跑测脚本（零重建路线）。

存在理由: R449/R451 两次「重建 prompt」路线均 VOID（文本层锚成立、调用/解码面不一致）。
修 = 弃重建, 让**产品自身**跑真实语料 ⇒ 锚自动成立（实发 prompt 由产品自己发出）。

保真点: 产品的门判 prev 取自产品自己的 `_lastReplyBySession` ⇒ 要让门吃到**真实上一轮回答**,
必须让桩后端按该会话真实回复作答: reply_map[第 i 轮 user_msg] = 第 i+1 行的 prev_reply。
每会话窗口多带 1 轮「种子轮」把 prev 建立起来 ⇒ 种子轮不计入测量集。

语料卫生（本轮实测）: 1,542 行中 **276 行属 cron 会话**（user_len 达 80k+ 的定时作业提示面）⇒
本构建器只用**非 cron 会话**, 并把该缺陷登记进 meta.hygiene。

用法: python3 build_real_grid.py
"""
import collections
import json
import pathlib

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
CORPUS = ROOT / "eval/rover/r449/real-corpus.jsonl"
OUT = ROOT / "eval/rover/r452/grid"
DEFAULT_REPLY = "桩应答(会话末轮): 已完成该步。"
# (会话, 窗口起点或 None=取尾, 窗口长度) —— 窗口首轮为种子轮, 其余为测量轮
SPEC = [("20260906_070359_b183e6e4", None, 33), ("20260905_132828_cbfa2160", 0, 9),
        ("20260905_102140_6ce72e21", 0, 9)]


def main():
    rows = [json.loads(l) for l in CORPUS.read_text(encoding="utf-8").splitlines() if l.strip()]
    by = collections.OrderedDict()
    for r in rows:
        by.setdefault(r["session"], []).append(r)
    hygiene = {"rows_total": len(rows),
               "rows_in_cron_sessions": sum(len(v) for s, v in by.items() if s.startswith("cron")),
               "rows_in_real_sessions": sum(len(v) for s, v in by.items() if not s.startswith("cron"))}
    turns, meta, rmap = [], [], {}
    seq = []  # R452: 按**调用序号**对齐的回复序列(比按文本查表更能保 prev 链: 重复消息不塌缩)
    for sess, start, count in SPEC:
        v = by[sess]
        s0 = max(0, len(v) - count) if start is None else start
        win = v[s0:s0 + count]
        for i, r in enumerate(win):
            turns.append(r["user_msg"])
            nxt = win[i + 1]["prev_reply"] if i + 1 < len(win) else ""
            rmap[r["user_msg"]] = nxt if nxt.strip() else DEFAULT_REPLY
            seq.append(nxt if nxt.strip() else DEFAULT_REPLY)
            meta.append({"turn": len(turns), "measured": i > 0, "session": sess, "mid": r["mid"],
                         "user_len": r["user_len"], "rule_label": r["label"],
                         "prev_reply_len": len(r["prev_reply"]),
                         "prev_chain_ok": bool(r["prev_reply"].strip()) if i > 0 else False})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "task-REAL.json").write_text(
        json.dumps({"note": "R452 真实语料产品原生跑测(会话序, 每会话首轮=种子不计测量)",
                    "turn_timeout_s": 900, "turns": turns}, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "reply-map.json").write_text(json.dumps(rmap, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "reply-seq.json").write_text(json.dumps(seq, ensure_ascii=False, indent=1), encoding="utf-8")
    m = [x for x in meta if x["measured"]]
    lab = collections.Counter(x["rule_label"] for x in m)
    lens = sorted(x["user_len"] for x in m)
    summary = {"turns_total": len(turns), "measured": len(m), "sessions": [s for s, _, _ in SPEC],
               "rule_label_measured": dict(lab),
               "user_len_measured": {"min": lens[0], "p50": lens[len(lens) // 2], "max": lens[-1]},
               "prev_chain_ok_measured": sum(1 for x in m if x["prev_chain_ok"]),
               "hygiene": hygiene,
               "note": "判定器读数只与这些轮的 rule_label 对比; 规则标签=关键词规则(可复算, 噪声已知)"}
    (OUT / "meta.json").write_text(json.dumps({"summary": summary, "turns": meta}, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
