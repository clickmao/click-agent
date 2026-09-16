#!/usr/bin/env python3
"""R505 快照清单器: adapter 落盘目录 → 逐调用清单(.txt) + 逐文件 sha256 清单(.json)。

设计要点（针对 R504 的「判分后被覆盖」缺陷）:
  * 清单在**阶段结束时立即**生成（由 runner 调用, 早于任何其它作业）;
  * 清单记 **sha256**, 使「文件被后来的进程改写」成为机械可检事件（判据 H10）;
  * 清单只读落盘目录, 不修改任何文件。

用法: python3 manifest_r505.py --dir <dir> --usage-out a.txt --manifest-out a.json [--side agent|codex|all]
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--usage-out", required=True)
    ap.add_argument("--manifest-out", required=True)
    ap.add_argument("--side", default="all", choices=["all", "agent", "codex"])
    ap.add_argument("--batch", default="")
    a = ap.parse_args()

    if not os.path.isdir(a.dir):
        print("[致命] 目录不存在: %s" % a.dir)
        return 3

    pat = "side-*.json" if a.side == "all" else "side-%s-*.json" % a.side
    files = sorted(glob.glob(os.path.join(a.dir, pat)))
    rows, man, bad = [], [], []
    for p in files:
        base = os.path.basename(p)
        raw = open(p, "rb").read()
        try:
            d = json.loads(raw.decode("utf-8-sig"))
        except Exception as e:
            bad.append({"file": base, "error": str(e)})
            continue
        u = ((d.get("response") or {}).get("usage") or {})
        side = d.get("side") or ("codex" if "-codex-" in base else "agent")
        model = ((d.get("request") or {}).get("upstream_request") or {}).get("model") or \
                ((d.get("request") or {}).get("model"))
        rows.append("%s side=%s in=%s out=%s model=%s" % (
            base, side,
            u.get("prompt_tokens") if u.get("prompt_tokens") is not None else u.get("input_tokens"),
            u.get("completion_tokens") if u.get("completion_tokens") is not None else u.get("output_tokens"),
            model))
        man.append({"file": base, "side": side, "sha256": hashlib.sha256(raw).hexdigest(),
                    "bytes": len(raw),
                    "in_tokens": u.get("prompt_tokens"), "out_tokens": u.get("completion_tokens")})

    for path, text in ((a.usage_out, "\n".join(rows) + ("\n" if rows else "")),
                       (a.manifest_out, json.dumps({"batch": a.batch, "dir": a.dir, "side": a.side,
                                                    "n_files": len(man), "files": man,
                                                    "parse_errors": bad},
                                                   ensure_ascii=False, indent=1) + "\n")):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    print("[R505-manifest] side=%s 文件 %d ⇒ %s / %s%s" % (
        a.side, len(man), os.path.basename(a.usage_out), os.path.basename(a.manifest_out),
        (" [解析失败 %d]" % len(bad)) if bad else ""))
    return 0 if not bad else 2


if __name__ == "__main__":
    raise SystemExit(main())
