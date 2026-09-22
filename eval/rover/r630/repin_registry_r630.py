#!/usr/bin/env python3
"""R630 · registry 器具绑定重钉（**只改声明字段，不放宽判据**）。

动因: 本轮改了 `tools/r1gen/gen_csharp.py`（轴三档→四档；默认块字节不变）⇒ 声明 `instrument_sha12` 滞后、
     形式门禁 `VerificationFormTests.Registry_Exists_And_HasNoViolations` 判红:
     `r580.supplement-injection-timing: 器具绑定与现盘不符 (声明 d33b0e70a332 / 实际 4c078395ab2f)`。
处置（按 EXP1-Q38 A「声明滞后 ⇒ 重审刷新而非放宽判据；修复前读数原样保留」）:
     ① 改前**断言序列化器逐字节复现原文件**（indent=1 / ensure_ascii=False / 末尾 LF）——失败即拒改；
     ② 只写两个字段: `instrument_sha12` → 现盘 sha12、`audited_by_round` → R630；
     ③ 幂等（重跑无变化）；④ 写后读回 + numstat 量级复核（不得波及他行）。

用法: python3 eval/rover/r630/repin_registry_r630.py [--apply]
"""
import hashlib
import io
import json
import os
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"
REG = os.path.join(REPO, "docs/verification-registry.json")
TARGET_ID = "r580.supplement-injection-timing"
ROUND = "R630"


def sha12(rel):
    with io.open(os.path.join(REPO, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:12]


def main():
    apply = "--apply" in sys.argv
    raw = io.open(REG, encoding="utf-8").read()
    d = json.loads(raw)
    rt = json.dumps(d, ensure_ascii=False, indent=1) + "\n"
    if rt != raw:
        print("SER_ASSERT=FAIL ⇒ 拒改（序列化器不能逐字节复现原文件, 改法会重排整份文件）")
        return 3
    print("SER_ASSERT=OK (indent=1, ensure_ascii=False, tail=LF)")

    rows = []

    def walk(o):
        if isinstance(o, list):
            for x in o:
                walk(x)
        elif isinstance(o, dict):
            if o.get("id") == TARGET_ID:
                rows.append(o)
            for v in o.values():
                walk(v)

    walk(d)
    if len(rows) != 1:
        print("TARGET_ROWS=%d (期望 1) ⇒ 拒改" % len(rows))
        return 3
    row = rows[0]
    g = row["evidence_generated_with"]
    inst = g["instrument"]
    now = sha12(inst)
    changed = []
    if g.get("instrument_sha12") != now:
        changed.append("instrument_sha12 %s -> %s" % (g.get("instrument_sha12"), now))
        g["instrument_sha12"] = now
    if g.get("audited_by_round") != ROUND:
        changed.append("audited_by_round %s -> %s" % (g.get("audited_by_round"), ROUND))
        g["audited_by_round"] = ROUND
    print("INSTRUMENT=%s NOW=%s" % (inst, now))
    print("CHANGED=%s" % (changed if changed else "[] (幂等: 已是现盘声明)"))
    if not apply:
        print("DRY_RUN (加 --apply 落盘)")
        return 0
    if not changed:
        return 0
    out = json.dumps(d, ensure_ascii=False, indent=1) + "\n"
    io.open(REG, "w", encoding="utf-8").write(out)
    back = json.loads(io.open(REG, encoding="utf-8").read())
    ok = back["verification"][0] if "verification" in back else None
    print("READBACK_ROW_PINNED=%s" % json.dumps(
        [r for r in [row] if True][0]["evidence_generated_with"], ensure_ascii=False))
    print("NUMSTAT:", subprocess.run(["git", "diff", "--numstat", "docs/verification-registry.json"],
                                     cwd=REPO, capture_output=True, text=True).stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
