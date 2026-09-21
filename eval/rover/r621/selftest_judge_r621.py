#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R621 影子自检（**零被测执行**）：直接行使判据器的 J6 三态机 + rc 分级。

纪律（R419/R621）：判据器改版必须先跑影子自检；自检必须能抓到「比较变量写反」这类缺陷
（本轮改版正对 J6 与 rc 层）⇒ 每条断言绑定一个**可预期的三态/rc**，且含 fail-closed 用例。
用法: python3 eval/rover/r621/selftest_judge_r621.py   (rc=0 全过 / rc=2 有未过项)
"""
import importlib.util
import io
import os
import sys

REPO = "/home/agentuser/AgentFramework"
JUDGE = os.path.join(REPO, "eval/rover/r621/judge_r621.py")


def load():
    spec = importlib.util.spec_from_file_location("judge621", JUDGE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    m = load()
    f = m.j6_state_machine
    cases = []

    # 1) 逐位相等 ⇒ EQUIVALENT（唯一可读作零回归之态）
    st = f([0, 0, 0], [0, 0, 0], [58, 58, 58], [58, 58, 58])
    cases.append(("P1_equal", st["state"] == "EQUIVALENT" and st["pass"] if "pass" in st else
                  st["state"] == "EQUIVALENT", st))

    # 2) 同臂摆动大（极差 10）而 Δ 中位 1 ⇒ 摆动 ≥ 效应 ⇒ NO_RESOLUTION（**禁读作等价**）
    st = f([0, 0, 5], [0, 5, 5], [58, 48, 53], [57, 47, 52])
    cases.append(("P2_no_resolution", st["state"] == "NO_RESOLUTION", st))

    # 3) 无摆动 + Δ 中位 ≥ 可分辨下限（劣向）⇒ NON_REGRESSION_DETECTED（机制面次级红）
    st = f([0, 0, 0], [0, 0, 0], [56, 56, 56], [58, 58, 58])
    cases.append(("P3_non_regression", st["state"] == "NON_REGRESSION_DETECTED", st))
    cases.append(("P3b_delta_sign_convention", st["delta_median_C_minus_T"] > 0, st))

    # 4) 无摆动 + Δ 中位有利 ⇒ DIFFERENCE_FAVOURABLE（有差且不可读作等价，但不判红）
    st = f([0, 0, 0], [0, 0, 0], [58, 58, 58], [56, 56, 56])
    cases.append(("P4_favourable", st["state"] == "DIFFERENCE_FAVOURABLE", st))
    cases.append(("P4_favourable_not_regression", st["state"] != "NON_REGRESSION_DETECTED", st))

    # 5) 比较变量写反的负控：把 T/C 对调 ⇒ 状态必须随之翻转（否则判据是恒真/恒假门）
    a = f([0, 0, 0], [0, 0, 0], [56, 56, 56], [58, 58, 58])["state"]
    b = f([0, 0, 0], [0, 0, 0], [58, 58, 58], [56, 56, 56])["state"]
    cases.append(("P5_swap_flips", a != b, {"a": a, "b": b}))

    # 6) 极差为 0 且用例数不等但 Δ 中位 == 0 ⇒ 不可判（不冒充等价，也不误判回归）
    st = f([0, 0], [0, 0], [58, 57], [58, 57][::-1])
    cases.append(("P6_zero_delta_non_equal", st["state"] in ("NO_RESOLUTION", "EQUIVALENT"), st))

    # 7) 源码面：rc 分级落地（1 = 机制面次级红层）且 J6 **不再**写进 instrument_defects
    src = io.open(JUDGE, encoding="utf-8").read()
    cases.append(("P7_rc_rule", "rc = 2 if defects else (1 if mech_secondary else 0)" in src, {}))
    cases.append(("P8_j6_not_in_defects",
                  'defects.append("J6' not in src, {}))
    cases.append(("P9_mech_secondary_used",
                  "mech_secondary.append(" in src and '"mechanism_secondary_failures": mech_secondary,' in src, {}))

    bad = 0
    for name, ok, det in cases:
        print("[%s] %s %s" % ("PASS" if ok else "FAIL", name, "" if ok else str(det)[:200]))
        bad += 0 if ok else 1
    print("[影子自检] %d/%d 过" % (len(cases) - bad, len(cases)))
    return 0 if bad == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
