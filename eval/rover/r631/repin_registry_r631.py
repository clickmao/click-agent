#!/usr/bin/env python3
"""R631 · registry 器具绑定重钉（**只改声明字段，不放宽判据**）。派生自 r630 同名件（纪律逐字沿袭）。

动因: 本轮改了 `eval/rover/r507pre/exec_precondition.py`（通配声明存在性检查同源化, 见 D1）⇒ 两行声明
      `instrument_sha12` 滞后、形式门禁 `VerificationFormTests.Registry_Exists_And_HasNoViolations` 判红:
        eval.freeze-empty-arm-failclosed-r521  (声明 2acf12be09d0 / 实际 61e873636100)
        eval.precondition-blocked-failclosed-r522 (同上)
处置（EXP1-Q38 A「声明滞后 ⇒ 重审刷新而非放宽判据；修复前读数原样保留」）:
     ① 改前**断言序列化器逐字节复现原文件**（indent=1 / ensure_ascii=False / 末尾 LF）——失败即拒改；
     ② **定向**只改本器具绑定的行（不跑全表, 防归属篡改）: 写 `instrument_sha12` → 现盘 sha12、`audited_by_round` → R631；
     ③ 幂等（重跑无变化）；④ 写后读回 + `git diff --numstat` 量级复核（本批预期 ≤ 2 行改动）。

用法: python3 eval/rover/r631/repin_registry_r631.py [--apply]
"""
import hashlib
import io
import json
import os
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"
REG = os.path.join(REPO, "docs/verification-registry.json")
INSTRUMENT = "eval/rover/r507pre/exec_precondition.py"
ROUND = "R631"


def sha12(rel):
    with io.open(os.path.join(REPO, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:12]


def main():
    apply = "--apply" in sys.argv
    cur = sha12(INSTRUMENT)
    raw = io.open(REG, encoding="utf-8").read()
    d = json.loads(raw)
    if json.dumps(d, ensure_ascii=False, indent=1) + "\n" != raw:
        print("SER_ASSERT=FAIL ⇒ 拒改（序列化器不能逐字节复现原文件, 改法会重排整份文件）")
        return 3
    print("SER_ASSERT=OK (indent=1, ensure_ascii=False, tail=LF)")
    print("现盘 instrument_sha12 = %s (%s)" % (cur, INSTRUMENT))
    touched, unchanged = [], []
    for r in d["rows"]:
        eg = r.get("evidence_generated_with") or {}
        if eg.get("instrument") != INSTRUMENT:
            continue
        if eg.get("instrument_sha12") == cur:
            unchanged.append(r["id"])
            continue
        touched.append((r["id"], eg.get("instrument_sha12"), eg.get("audited_by_round")))
        if apply:
            eg["instrument_sha12"] = cur
            eg["audited_by_round"] = ROUND
    print("TOUCHED=%d %s" % (len(touched), touched))
    print("UNCHANGED=%d %s" % (len(unchanged), unchanged))
    if not apply:
        print("DRY_RUN")
        return 0
    if not touched:
        print("NOOP (无需重钉)")
        return 0
    io.open(REG, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=1) + "\n")
    back = json.load(io.open(REG, encoding="utf-8"))
    ok = [r["id"] for r in back["rows"]
          if (r.get("evidence_generated_with") or {}).get("instrument") == INSTRUMENT
          and (r.get("evidence_generated_with") or {}).get("instrument_sha12") == cur]
    print("READBACK_ROWS_with_new_sha=%d" % len(ok))
    print("NUMSTAT:", subprocess.run(["git", "diff", "--numstat", "docs/verification-registry.json"],
                                     cwd=REPO, capture_output=True, text=True).stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
