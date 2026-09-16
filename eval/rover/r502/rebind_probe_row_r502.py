#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R502: 定向重钉 `probe.randomized-selfcheck` 行（器具已改 ⇒ R2e 要求重审）。

为何不用 bind_evidence.py: 该工具序列化器写 **indent=1**，而本仓登记表现盘是 **indent=2**
（另一写者落盘）⇒ `SER_ASSERT=FAIL`（工具自带的 fail-closed 防格式漂移），且即便在
indent=1 的 scratch 副本上，apply 只刷 audited_by_round、不重钉 instrument_sha12 ⇒ 违规仍在。
本器具 = **保原文格式的定向字段更新**：只改 3 个字段，其余字节逐位不变，并在写后断言:
  ① json.load(新) == 期望对象（旧对象 + 3 处字段改动）;
  ② 逐行 diff 只落在含这 3 个字段名的行上（其余行字节相同）;
  ③ 幂等（再跑一次得到同一字节）。

用法:
  python3 eval/rover/r502/rebind_probe_row_r502.py --artifact <evidence.json> --round R502 [--check]
退出码: 0 = 已重钉并核验 / 1 = 校验失败 / 3 = 输入缺失
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys

REG = "docs/verification-registry.json"
ROW = "probe.randomized-selfcheck"
FIELDS = ("instrument_sha12", "artifact_sha12", "audited_by_round")


def sha12(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]


def detect_fmt(raw):
    """按现盘字节推断序列化参数（保持原文格式 ⇒ 不被格式漂移污染）。"""
    ind = 1 if raw.startswith('{\n "') else 2
    esc = ("\\u" in raw)
    return ind, (not esc)   # (indent, ensure_ascii)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--round", required=True)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if not os.path.isfile(a.artifact) or not os.path.isfile(REG):
        print("[致命] 输入缺失")
        return 3
    raw = io.open(REG, encoding="utf-8").read()
    indent, ensure_ascii = detect_fmt(raw)
    doc = json.loads(raw)
    row = [r for r in doc["rows"] if r.get("id") == ROW]
    if len(row) != 1:
        print("[致命] 行定位失败 id=%s n=%d" % (ROW, len(row)))
        return 3
    row = row[0]
    new_sha = sha12(a.artifact)
    old = dict(row["evidence_generated_with"])
    new = {"instrument": "eval/probe/tasks.py",
           "instrument_sha12": sha12("eval/probe/tasks.py"),
           "artifact_sha12": new_sha,
           "audited_by_round": a.round}
    for k, v in new.items():
        row["evidence_generated_with"][k] = v

    out = json.dumps(doc, ensure_ascii=ensure_ascii, indent=indent) + "\n"
    # 断言 ① json 等价于期望对象
    want = json.loads(raw)
    for r in want["rows"]:
        if r.get("id") == ROW:
            r["evidence_generated_with"].update(new)
    if json.loads(out) != want:
        print("[致命] 写入对象 != 期望（拒绝落盘）")
        return 1
    # 断言 ② 逐行 diff 只落在含目标字段名的行
    lo, ln = raw.splitlines(), out.splitlines()
    if len(lo) != len(ln):
        print("[致命] 行数变化 %d -> %d" % (len(lo), len(ln)))
        return 1
    changed = [i for i, (x, y) in enumerate(zip(lo, ln)) if x != y]
    bad = [i for i in changed if not any(('"%s"' % f) in ln[i] for f in FIELDS)]
    if bad:
        print("[致命] 越界改动行: %s" % [i + 1 for i in bad])
        return 1
    if a.check:
        print("[check] 待改字段: %s -> %s ; 改动行 %d" % (old.get("instrument_sha12"), new["instrument_sha12"], len(changed)))
        return 0
    io.open(REG, "w", encoding="utf-8", newline="\n").write(out)
    # 断言 ③ 幂等
    again = json.dumps(json.loads(io.open(REG, encoding="utf-8").read()), ensure_ascii=ensure_ascii, indent=indent) + "\n"
    if again != out:
        print("[致命] 非幂等")
        return 1
    print("[OK] %s 重钉: instrument_sha12=%s artifact_sha12=%s audited_by_round=%s (改动行 %d)"
          % (ROW, new["instrument_sha12"], new["artifact_sha12"], new["audited_by_round"], len(changed)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
