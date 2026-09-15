#!/usr/bin/env python3
"""R460 归因器具: 从**实发全量消息** (adapter ADAPTER_DUMP_FULL=1) 逐块量注入体量。

纪律:
  · 只读实发文本 (full-*.json), 不重建 prompt; 文件缺失 ⇒ 报 VOID, 不得下结论;
  · 只做「块长统计 + 命中率/token 汇总」, 不做语义判断;
  · 逐调用输出 miss 绝对值 (miss = prompt - cached), 命中率 = cached/prompt。
"""
import glob
import io
import json
import os
import sys

MARKERS = [
    "[会话基线 v1]",
    "[本轮参考上下文]",
    "[SessionMemory",
    "[下轮预估",
    "[承接状态 v1]",
    "[工作区",
    "[动作",
]

DIR = sys.argv[1] if len(sys.argv) > 1 else "/tmp/r460_env/logs/adapter"


def blocks_of(text):
    """按 marker 切块; 返回 [(name, chars)] 与剩余裸文本长度。"""
    pos = []
    for m in MARKERS:
        i = text.find(m)
        if i >= 0:
            pos.append((i, m))
    pos.sort()
    out = []
    for idx, (i, m) in enumerate(pos):
        end = pos[idx + 1][0] if idx + 1 < len(pos) else len(text)
        out.append((m, end - i))
    head = pos[0][0] if pos else len(text)
    return head, out


def main():
    sides = sorted(glob.glob(os.path.join(DIR, "side-agent-*.json")))
    if not sides:
        print("VOID: 无 side-agent-*.json ⇒ 未取证")
        return
    rows = []
    for f in sides:
        d = json.load(io.open(f, encoding="utf-8"))
        u = (d["response"].get("usage") or {})
        p = u.get("prompt_tokens") or 0
        c = u.get("prompt_tokens_details", {}).get("cached_tokens") if isinstance(u.get("prompt_tokens_details"), dict) else u.get("cached_tokens")
        c = c or 0
        rows.append((os.path.basename(f), p, c, p - c))
    tp = sum(r[1] for r in rows)
    tc = sum(r[2] for r in rows)
    tm = sum(r[3] for r in rows)
    print(f"我方调用 n={len(rows)}  prompt ∑={tp}  cached ∑={tc}  hit={tc/tp*100:.1f}%  miss ∑={tm}  miss均价={tm/len(rows):.0f}")
    steady = rows[1:]
    sp = sum(r[1] for r in steady)
    sc = sum(r[2] for r in steady)
    print(f"  稳态(2..n) n={len(steady)}  hit={sc/sp*100:.1f}%  miss均价={(sp-sc)/len(steady):.0f}")
    for r in rows:
        print(f"    {r[0]:22s} prompt={r[1]:6d} cached={r[2]:6d} miss={r[3]:5d} hit={r[2]/r[1]*100:5.1f}%")

    fulls = sorted(glob.glob(os.path.join(DIR, "full-agent-*.json")))
    if not fulls:
        print("VOID(块归因): 无 full-agent-*.json (ADAPTER_DUMP_FULL 未开) ⇒ 禁重建/禁估算")
        return
    print("\n=== 每调用: 最后一条 user 消息的块组成 (实发文本) ===")
    for f in fulls:
        msgs = json.load(io.open(f, encoding="utf-8"))
        last = None
        for m in msgs:
            if m.get("role") == "user":
                last = m
        if last is None:
            continue
        t = last.get("content") or ""
        head, bl = blocks_of(t)
        parts = " ".join(f"{n}={c}" for n, c in bl)
        print(f"  {os.path.basename(f):24s} msgs={len(msgs)} lastuser={len(t):5d} 裸文本={head:4d} {parts}")


main()
