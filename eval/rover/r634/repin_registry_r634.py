#!/usr/bin/env python3
"""R634 · registry 器具绑定重钉（**只改声明字段，不放宽判据**）。派生自 r631 同名件（纪律逐字沿袭）。

动因: 本轮 E4 自捕（`quality_core` 已算 `truth_self_failed_cases`/`truth_ran_per_window`，汇总裁剪时**未发射**
      ⇒ 判据算出的关键列在判决件里读不到 ⇒ 「自败例逐条单列」不可判）⇒ 修判据器发射面（判据本体与阈值**零改动**，
      修后 rc/valid/D 逐值不变）⇒ 本行 `instrument_sha12` 滞后，须重钉 + note 追加 E4。
处置（EXP1-Q38 A「声明滞后 ⇒ 重审刷新而非放宽判据；修复前读数原样保留」）:
     ① 改前**断言序列化器逐字节复现原文件**（indent=1 / ensure_ascii=False / 末尾 LF）——失败即拒改；
     ② **定向**只改本器具绑定的行（不跑全表, 防归属篡改）；
     ③ 幂等（重跑无变化）；④ 写后读回 + `git diff --numstat` 量级复核。

用法: python3 eval/rover/r634/repin_registry_r634.py [--apply]
"""
import hashlib
import io
import json
import os
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"
REG = os.path.join(REPO, "docs/verification-registry.json")
INSTRUMENT = "eval/rover/r634/judge_r634.py"
ROUND = "R634"
E4 = ("；E4（自捕，同轮修）: 判据器 `quality_core` 已算 `truth_self_failed_cases`/`truth_ran_per_window` 但汇总裁剪"
      "**未发射** ⇒ 「自败例逐条单列」在判决件里不可判；修 = 无条件发射该两键（判据本体/阈值零改动，修后 "
      "rc=1 / valid=3 / D=[0,−3,−5] 逐值不变）。")


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
        note = r.get("note") or ""
        need_note = "E4" not in note
        if eg.get("instrument_sha12") == cur and not need_note:
            unchanged.append(r["id"])
            continue
        touched.append((r["id"], eg.get("instrument_sha12"), cur, need_note))
        if apply:
            eg["instrument_sha12"] = cur
            eg["audited_by_round"] = ROUND
            if need_note:
                r["note"] = note.rstrip() + E4
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
    print("READBACK_E4_in_note=%d" % len([r for r in back["rows"] if r["id"] in ok and "E4" in (r.get("note") or "")]))
    print("NUMSTAT:", subprocess.run(["git", "diff", "--numstat", "docs/verification-registry.json"],
                                     cwd=REPO, capture_output=True, text=True).stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
