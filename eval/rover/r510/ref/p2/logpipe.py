#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R508 P2 参考解 (oracle): 日志分析 CLI logpipe —— 判据器正控。
契约与 taskset-r508.json 中 p2 的 prompt 逐条对应 (标准库 only)。"""
from __future__ import annotations
import argparse, json, math, re, sys

LINE = re.compile(r'^(\S+) (\S+) (\S+) \[([^\]]+)\] "([^"]*)" (\d{3}) (\d+|-)$')


def parse(text: str):
    total, skipped = 0, 0
    status, ipc, sizes = {}, {}, []
    for raw in text.splitlines():
        if not raw.strip():
            skipped += 1
            continue
        m = LINE.match(raw.strip())
        if not m:
            skipped += 1
            continue
        total += 1
        ip, code, size = m.group(1), m.group(6), m.group(7)
        status[code] = status.get(code, 0) + 1
        ipc[ip] = ipc.get(ip, 0) + 1
        sizes.append(0 if size == "-" else int(size))
    return total, skipped, status, ipc, sizes


def p95(values):
    if not values:
        return 0
    s = sorted(values)
    idx = int(math.ceil(0.95 * len(s))) - 1
    return s[max(0, min(idx, len(s) - 1))]


def build(text: str, top: int) -> dict:
    total, skipped, status, ipc, sizes = parse(text)
    items = sorted(ipc.items(), key=lambda kv: (-kv[1], kv[0]))[:max(0, top)]
    return {
        "total": total,
        "skipped": skipped,
        "status_counts": {k: status[k] for k in sorted(status, key=int)},
        "top_ips": [{"ip": k, "count": v} for k, v in items],
        "p95_bytes": p95(sizes),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", required=True)
    ap.add_argument("--top", type=int, default=3)
    a = ap.parse_args()
    try:
        with open(a.inp, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        text = ""
    rep = build(text, a.top)
    with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, ensure_ascii=False)
    print(json.dumps(rep, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
