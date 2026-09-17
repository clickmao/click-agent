#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R518 证据归档 (幂等): 把 /tmp 运行面的关键证据按 sha256 复制进仓库, 落索引。

纪律: ①逐文件 (bytes, sha256) 记录, 读回校验; ②目标已存在且 sha 不同 ⇒ 拒写 (禁静默覆盖);
③只归档本轮产物, 不改动运行目录。
"""
from __future__ import annotations
import hashlib, io, json, os, shutil, sys

REPO = "/home/agentuser/AgentFramework"
OUT = os.path.join(REPO, "eval/rover/r518/evidence")
AC_RUN = "/tmp/r518/run-0917-131155"        # w2 的 A/C 臂 (计量正确)
VOID_RUN = "/tmp/r518/run-0917-130514"      # w1 作废窗
ORCH_RUN = "/tmp/r518/orch-0917-132218"     # O 臂重跑 (缓存修复后)

ITEMS = [
    (os.path.join(AC_RUN, "report.json"), "w2-aggregate-report.json"),
    (os.path.join(AC_RUN, "A-r1", "side-run.json"), "w2-arm-A-side-run.json"),
    (os.path.join(AC_RUN, "C-r1", "side-run.json"), "w2-arm-C-side-run.json"),
    (os.path.join(ORCH_RUN, "orch", "report.json"), "orch-report-r518.json"),
    (os.path.join(ORCH_RUN, "SUMMARY-r518-orch.txt"), "orch-summary-r518.txt"),
    (os.path.join(REPO, "eval/rover/r507pre/precondition-r518.json"), "precondition-r518.json"),
    ("/tmp/r518/nc.json", "nc-contract-r518.json"),
    ("/tmp/pub_r518.log", "aot-pub-r518.log"),
    ("/tmp/pub_r518b.log", "aot-pub-r518b-cachefix.log"),
    (os.path.join(VOID_RUN, "SUMMARY-r518.txt"), "void-w1-summary.txt"),
]


def sha256_of(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    idx, skipped = [], []
    for src, name in ITEMS:
        if not os.path.isfile(src):
            print("[警告] 缺 %s ⇒ 跳过 (fail-open 仅限缺件, 不静默)" % src)
            skipped.append(name)
            continue
        dst = os.path.join(OUT, name)
        s = sha256_of(src)
        if os.path.isfile(dst):
            if sha256_of(dst) != s:
                print("[致命] %s 已存在且 sha 不同 ⇒ 拒写 (禁静默覆盖)" % dst)
                return 3
            idx.append({"name": name, "src": src, "bytes": os.path.getsize(dst), "sha256": s, "state": "unchanged"})
            continue
        shutil.copy2(src, dst)
        got = sha256_of(dst)
        if got != s:
            print("[致命] 读回校验失败 %s" % dst)
            return 3
        idx.append({"name": name, "src": src, "bytes": os.path.getsize(dst), "sha256": s, "state": "copied"})
    io.open(os.path.join(OUT, "index-r518.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps({"round": "R518", "run_dirs": {"w2_ac": AC_RUN, "orch": ORCH_RUN, "void_w1": VOID_RUN},
                    "items": idx, "skipped": skipped}, ensure_ascii=False, indent=1) + "\n")
    print("ARCHIVE_OK n=%d skipped=%d" % (len(idx), len(skipped)))
    for it in idx:
        print("  %-36s %8d  %s" % (it["name"], it["bytes"], it["sha256"][:16]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
