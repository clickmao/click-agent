#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R508 读数器: 从 adapter 落盘 (side-<side>-NNN.json) 汇总 调用数/tokens/模型名。

口径 (沿用 R502/R505):
  calls          = 去重后的请求文件数 (按 NNN 索引范围过滤)
  prompt_tokens  = 上游 usage.prompt_tokens 之和 (真值取上游 usage, 不外推)
  cached_tokens  = usage.prompt_tokens_details.cached_tokens 之和
  completion     = usage.completion_tokens 之和
  total          = usage.total_tokens 之和
  models         = request.upstream_request.model 去重集合 (H4 同模型判据)
  unreported     = usage 缺失的调用数 (禁按 0 冒充; 单项计入 unreported)
"""
from __future__ import annotations
import argparse, json, os, re, sys

FNAME = re.compile(r"^side-([a-z0-9_]+)-(\d+)\.json$")


def collect(d, side, idx_from=1, idx_to=10 ** 9):
    calls = 0
    p = c = comp = tot = 0
    models = set()
    unreported = 0
    files = []
    for fn in sorted(os.listdir(d)):
        m = FNAME.match(fn)
        if not m or m.group(1) != side:
            continue
        idx = int(m.group(2))
        if idx < idx_from or idx > idx_to:
            continue
        try:
            blob = json.load(open(os.path.join(d, fn), encoding="utf-8"))
        except Exception as e:
            files.append({"file": fn, "error": str(e)[:80]})
            continue
        calls += 1
        req = (blob.get("request") or {}).get("upstream_request") or {}
        if req.get("model"):
            models.add(str(req["model"]))
        u = (blob.get("response") or {}).get("usage") or {}
        if not u:
            unreported += 1
        p += int(u.get("prompt_tokens") or 0)
        comp += int(u.get("completion_tokens") or 0)
        tot += int(u.get("total_tokens") or 0)
        c += int((u.get("prompt_tokens_details") or {}).get("cached_tokens") or u.get("prompt_cache_hit_tokens") or 0)
        files.append({"file": fn, "pt": u.get("prompt_tokens"), "ct": u.get("completion_tokens"),
                      "model": req.get("model")})
    return {"side": side, "dir": d, "range": [idx_from, idx_to], "calls": calls,
            "prompt_tokens": p, "cached_tokens": c, "completion_tokens": comp, "total_tokens": tot,
            "models": sorted(models), "unreported_usage": unreported, "files": files}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--side", required=True)
    ap.add_argument("--from", dest="i0", type=int, default=1)
    ap.add_argument("--to", dest="i1", type=int, default=10 ** 9)
    ap.add_argument("--json")
    a = ap.parse_args()
    out = collect(a.dir, a.side, a.i0, a.i1)
    print(json.dumps({k: v for k, v in out.items() if k != "files"}, ensure_ascii=False))
    if a.json:
        json.dump(out, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
