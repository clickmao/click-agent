#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R514 · 判据器**影子自检**: 合成 report × 臂/模式组合, 逐条断言预期退出码与三态判决。

动机: 真机臂昂贵且一次只跑一遍 ⇒ 判据器上线前必须先跑合成自检 (唯一廉价闸)。本自检必须能抓到
「比较变量写反」(A/C 互换必须改变判决) 这类缺陷 —— 只测「正常批通过」等于没测。

覆盖面 (每条臂断言预期 rc 与预期判决, 期望落机读字段):
  S1 正常批 (调用数下降 + token n≥5 中位达标)        → rc=0 PASS
  S2 token 中位越线                                  → rc=1 BREACH
  S3 调用数比 > 1 (更差)                             → rc=1 BREACH
  S4 调用数比全部 == 1 (不更差但无下降)               → rc=1 BREACH (「无下降」不得判过)
  S5 跑次 n < n_min                                  → rc=0 且 C2 状态 = ABSTAIN_N_BELOW_MIN (弃权不判红/绿)
  S6 usage 未上报 > 0                                → rc=0 且 C2 状态 = ABSTAIN_UNREPORTED_USAGE
  S7 A/C 互换 (比较变量写反)                          → 判决必须翻转 (S1 的 PASS → BREACH)
  S8 缺 C 侧                                        → rc=3 MISSING_SIDE
  S9 预注册缺 declared_noise_sources                  → rc=2 fail-closed (禁硬编码噪声源)
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, "check_criteria_r514.py")
PREREG = {
    "criteria": {
        "C1_calls_primary": {"rule": "逐(窗口,题) agent_calls/codex_calls <= 1.0 且 min < 1.0 (规则式, 无常数)"},
        "C2_token_median": {"rule": "中位数 token 比值 <= 0.80 * 1 且跑次 n >= 5"},
    },
    "declared_noise_sources": ["codex 侧跨跑次用量 2 倍级摆动 (R513 实测 849,925–1,266,833)",
                               "上游空正文/续调用 (按 unreported_usage 单列)",
                               "同机争用对墙钟的影响 (墙钟不作判据)"],
}


def rows(runs, agent_calls, codex_calls, agent_tok, codex_tok, cases_a=12, cases_c=12, unreported=0):
    out = []
    for i in range(runs):
        for arm, calls, tok, cs in (("A", agent_calls, agent_tok, cases_a), ("C", codex_calls, codex_tok, cases_c)):
            out.append({"arm": arm, "run": "%s-r%d" % (arm, i + 1), "tid": "p4", "all_pass": cs == 12,
                        "cases_pass": cs, "cases_total": 12, "failed": [], "calls": calls,
                        "total_tokens": tok, "unreported_usage": unreported, "elapsed_s": 30.0})
    return {"rows": out, "arms": []}


def run(rep, pre, tag):
    with tempfile.TemporaryDirectory(prefix="r514shadow-") as d:
        rp, pp = os.path.join(d, "report.json"), os.path.join(d, "prereg.json")
        json.dump(rep, open(rp, "w", encoding="utf-8", newline="\n"), ensure_ascii=False)
        json.dump(pre, open(pp, "w", encoding="utf-8", newline="\n"), ensure_ascii=False)
        p = subprocess.run([sys.executable, CHECK, "--report", rp, "--prereg", pp],
                           capture_output=True, text=True)
        return p.returncode, p.stdout


def swap_ac(rep):
    for r in rep["rows"]:
        if r["arm"] == "A":
            r["arm"] = "C0"
        elif r["arm"] == "C":
            r["arm"] = "A"
    for r in rep["rows"]:
        if r["arm"] == "C0":
            r["arm"] = "C"
    return rep


def main():
    arms, fails = [], []

    def case(tag, expect_rc, expect_sub=None, report=None, prereg=None, mutate=None):
        rep = mutate(json.loads(json.dumps(report))) if mutate else report
        rc, out = run(rep, prereg or PREREG, tag)
        ok = rc == expect_rc and (expect_sub is None or expect_sub in out)
        arms.append({"tag": tag, "inject_expect_rc": expect_rc, "rc": rc,
                     "expect_substr": expect_sub, "ok": ok, "stdout_head": out[:240]})
        if not ok:
            fails.append(tag)

    base = rows(5, 7, 14, 70_000, 400_000)
    case("S1_normal_pass", 0, "verdict=PASS", base)
    case("S2_token_median_breach", 1, "verdict=BREACH", rows(5, 7, 14, 380_000, 400_000))
    case("S3_calls_worse", 1, "verdict=BREACH", rows(5, 15, 14, 70_000, 400_000))
    case("S4_calls_equal_no_gain", 1, "verdict=BREACH", rows(5, 14, 14, 70_000, 400_000))
    case("S5_n_below_min_abstain", 0, "ABSTAIN_N_BELOW_MIN", rows(3, 7, 14, 70_000, 400_000))
    case("S6_unreported_usage_abstain", 0, "ABSTAIN_UNREPORTED_USAGE", rows(5, 7, 14, 70_000, 400_000, unreported=2))
    case("S7_ac_swapped_flips_verdict", 1, "verdict=BREACH", base, None, swap_ac)
    case("S8_missing_codex_side", 3, "MISSING_SIDE", {"rows": [r for r in rows(5, 7, 14, 70_000, 400_000)["rows"]
                                                              if r["arm"] == "A"], "arms": []})
    bad_pre = json.loads(json.dumps(PREREG)); bad_pre.pop("declared_noise_sources")
    case("S9_prereg_no_noise_declared", 2, "器具缺陷", base, bad_pre)

    doc = {"arms": arms, "verdict": "OK" if not fails else "FAIL", "failed_arms": fails,
           "checker_sha256": hashlib.sha256(open(CHECK, "rb").read()).hexdigest(),
           "prereg_sha256": hashlib.sha256(json.dumps(PREREG, ensure_ascii=False, sort_keys=True)
                                           .encode("utf-8")).hexdigest()}
    outp = os.path.join(HERE, "evidence", "shadow-selftest-r514.json")
    os.makedirs(os.path.dirname(outp), exist_ok=True)
    json.dump(doc, open(outp, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    for a in arms:
        print("%-32s expect_rc=%d rc=%d %s" % (a["tag"], a["inject_expect_rc"], a["rc"], "OK" if a["ok"] else "FAIL"))
    print("verdict=%s failed=%s" % (doc["verdict"], fails or "-"))
    return 0 if doc["verdict"] == "OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
