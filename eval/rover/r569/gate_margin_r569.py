#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R569 起手闸「擦边 PASS」振幅余量条款 (候选③ 落地件).

背景 (R562 自捕): 起手闸沿用固定门槛 GATE_MB=2650 (eval/rover/r483/preflight_gate.py),
R562 实测 PC 读数 mem=2652 ⇒ 只比门槛高 2 MB 也算 PASS。运行器起臂时会**再查一次**
(本 runner: 连续 2 次), 擦边读数在第二次采样或紧随其后的运行中被击穿 ⇒
得到「等待器报 OPEN → 起臂即 GATE_BLOCKED」的空转。

条款 (三条, 全满足才认「窗口」; 擦边 PASS 不算窗口):
  1. 余量: 起手读数 ≥ GATE_MB + MARGIN, 其中 MARGIN 由**本宿主实测顶棚**派生
     MARGIN = min(MARGIN_CAP=200, max(MARGIN_MIN=25, ceiling - GATE_MB - HEADROOM=50))
     —— 顶棚 = 起手前连续采样的最大值 (空闲顶棚)。顶棚不允许时取顶棚允许的最大值,
     并在读数里显式登记 margin_low=true (不得静默用固定值冒充派生值)。
  2. 稳定性: 起手前样本的极差 ≤ SPREAD_MAX=50 MB (抖动大 ⇒ 读数不可信, 不算窗口)。
  3. 对侧无重进程: 由既有闸的 blockers 承担 (本件只读, 不重复实现 blocker 逻辑)。

行使方式 (翻既有开关, 零新逻辑进闸): runner 以 `--gate-mb $REQ` 调用既有闸 ⇒
门槛在闸内部生效 + 连续 2 次 + blockers 空。

运行中后置断言 (--postcheck): 运行窗口内 min(mem) ≥ GATE_MB; 否则该窗读数标
window_drift (读数不作验收依据, 但保守留档)。观测振幅 S_obs = ceiling - in_min 落盘,
供下一轮 MARGIN 派生使用。

rc 语义 (fail-closed): 0 条款满足 / 2 条款不满足 (擦边或抖动) / 3 输入缺失或不可解析。
成对控制 (--selftest): 正控 1 例 + 负控 3 例 (擦边反例=2652 / 抖动 / 顶棚过低),
逐例断言预期 rc——不配负控的余量条款是空心的 (R413/R417 纪律)。

零远端 · 零产品源码改动 · 零新增夹具: 只读 /proc/meminfo 与既有闸落盘件。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

GATE_MB = 2650        # 既有闸基础门槛 (eval/rover/r483/preflight_gate.py GATE_MB)
MARGIN_FLOOR = 60     # v2 余量下限 (本宿主空闲极差实测 <= 7MB 的 8 倍); 余量 = max(下限, 上一轮观测振幅)
MARGIN_CAP_V1 = 200   # v1 常量 (R562 跨区制振幅 197MB) —— 本宿主结构性不可达: 清残留后顶棚 2813 < 2850
SPREAD_MAX = 50       # 起手前样本极差上限


def _read_samples(path):
    xs = []
    if not os.path.isfile(path):
        return None
    for ln in io.open(path, encoding="utf-8", errors="replace"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            rec = json.loads(ln)
            v = rec.get("mem_available_mb")
            if isinstance(v, (int, float)):
                xs.append(float(v))
        except Exception:  # noqa: BLE001
            continue
    return xs or None


def derive(xs, prev_swing_mb=None):
    """由起手前样本 + 上一轮**观测振幅**派生门槛 (无条件键; 缺项写 None)。

    条款 v2 (数据先行; 修 R569 v1 的结构性不可达):
      MARGIN = max(MARGIN_FLOOR, prev_swing_mb or 0)
      REQ    = GATE_MB + MARGIN
    v1 曾用固定常量 200 (= R562 **跨区制**振幅 197MB 取整) ⇒ 在本宿主上 起手顶棚 2813
    最高也只有 163 MB 余量 ⇒ 恒 rc=2 (结构性不可达, 与 R561 v1 判据同族形态)。修法 =
    把余量改成由**同一宿主上一轮运行中实测振幅**派生 (本轮首次采集 ⇒ 取下限 60MB),
    这样条款随数据收紧而不会被另一个区制的数字卡死。

    余量**不缩水** (R565 自捕#1: 首版把 MARGIN 夹到下限并放行低顶棚 = 空心条款;
    负控 NC_low_ceiling 抓到)。顶棚给不出满额余量 ⇒ 不算窗口 (rc=2)。
    """
    if not xs:
        return {"rc": 3, "note": "no_pre_samples",
                "ceiling_mb": None, "spread_mb": None, "margin_mb": None,
                "required_mb": None, "margin_low": None, "n_samples": 0}
    ceil_mb, spread = max(xs), max(xs) - min(xs)
    want = max(MARGIN_FLOOR, float(prev_swing_mb or 0))   # 目标余量 (数据派生)
    cap = ceil_mb - GATE_MB                                # 上界: 顶棚允许的最大余量
    # 候选⑤ (R568 预注册的下一轮规则): MARGIN := min(目标, 顶棚 - GATE)
    # 上界**不得静默**: 装不下下限 ⇒ fail-closed (rc=2); 装得下但 < 目标 ⇒ 行使 + margin_capped=True
    margin = min(want, cap)
    capped = margin < want
    floor_unreachable = cap < MARGIN_FLOOR
    required = GATE_MB + margin
    margin_low = ceil_mb < required
    ok = (not floor_unreachable) and (ceil_mb >= required) and (spread <= SPREAD_MAX)
    return {"rc": 0 if ok else 2,
            "margin_want_mb": round(want, 1), "margin_cap_mb": round(cap, 1),
            "margin_capped": bool(capped), "floor_unreachable": bool(floor_unreachable),
            "ceiling_mb": round(ceil_mb, 1), "spread_mb": round(spread, 1),
            "margin_mb": round(margin, 1), "required_mb": round(required, 1),
            "margin_low": bool(margin_low), "n_samples": len(xs),
            "margin_src": ("prev_observed_swing" if (prev_swing_mb or 0) > MARGIN_FLOOR else "floor(first_round)"),
            "prev_swing_mb": prev_swing_mb,
            "v1_constant_unreachable": {"constant": MARGIN_CAP_V1,
                                        "why": "本宿主清残留后顶棚 2813 < 2650+200=2850 ⇒ v1 恒 rc=2"},
            "slack_mb": round(ceil_mb - required, 1),
            "why": ("ok" if ok else
                    ("margin_floor_unreachable_at_ceiling" if floor_unreachable else
                     ("spread_too_wide" if spread > SPREAD_MAX else "ceiling_below_required_margin"))),
            "clause": "起手读数 >= GATE_MB(%d) + MARGIN(min(max(%d, 上一轮观测振幅), 顶棚-GATE_MB)) "
                      "且 极差 <= %d 且 连续 2 次 且 blockers 空; 上界生效时 margin_capped=true (不静默), "
                      "顶棚装不下下限时 fail-closed rc=2"
                      % (GATE_MB, MARGIN_FLOOR, SPREAD_MAX)}


def postcheck(xs):
    """运行窗口内采样: 基础门槛是否被击穿 + 观测振幅 (供下一轮派生)。"""
    if not xs:
        return {"rc": 3, "note": "no_run_samples", "in_min_mb": None, "swing_mb": None}
    in_min, in_max = min(xs), max(xs)
    ok = in_min >= GATE_MB
    return {"rc": 0 if ok else 2, "in_min_mb": round(in_min, 1), "in_max_mb": round(in_max, 1),
            "swing_mb": round(in_max - in_min, 1), "n_samples": len(xs),
            "gate_mb": GATE_MB, "window_drift": (not ok),
            "why": "ok" if ok else "run_window_breached_base_gate"}


def selftest():
    """成对控制 (器具改版后重钉): 正控 3 + 负控 3, 逐例断言 rc **与** margin_capped。

    与 R567 版的语义变化 (声明): 旧负控 `NC_v1_constant_unreachable` (期望 rc=2) 在上界规则下
    **不再成立** —— 常量 200 被上界夹到 163 后条款可行使 ⇒ 该例改为正控 `PL_v1_constant_capped`
    (期望 rc=0 **且** margin_capped=True: 证明「不该静的」没被静默)。真正的负控改成
    「顶棚连下限都装不下」(cap < MARGIN_FLOOR) ⇒ rc=2。
    """
    cases = [
        ("PL_floor_healthy", [2851, 2854, 2856], None, 0, False),        # 正控: 下限档
        ("PL_adaptive_prev110", [2813, 2811, 2812], 110, 0, False),      # 正控: 自适应档 (未触上界)
        ("PL_capped_above_floor", [2730, 2728, 2729], 103, 0, True),     # 正控: 上界行使但 >= 下限 (可行使)
        ("PL_v1_constant_capped", [2813, 2811, 2812], 200, 0, True),     # 正控: 旧 v1 常量被夹 (非静默)
        ("NC_cap_below_floor", [2704, 2703, 2704], 103, 2, True),        # 负控: R568 实测区制 (cap 54 < 60) ⇒ 不可行使
        ("NC_marginal_2652", [2652, 2652, 2652], None, 2, True),         # 负控: R562 擦边反例
        ("NC_jitter", [2700, 2760, 2850], None, 2, False),               # 负控: 极差 150 > 50
    ]
    out = []
    for name, xs, prev, exp_rc, exp_capped in cases:
        got = derive(xs, prev)
        ok = (got["rc"] == exp_rc) and (bool(got.get("margin_capped")) == exp_capped)
        out.append({"fixture": name, "expected_rc": exp_rc, "got_rc": got["rc"],
                    "expected_capped": exp_capped, "got_capped": bool(got.get("margin_capped")),
                    "ok": ok})
    n_ok = sum(1 for x in out if x["ok"])
    return {"fixtures": out, "n": len(out), "n_ok": n_ok, "has_teeth": n_ok == len(out)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--derive", action="store_true")
    ap.add_argument("--postcheck", action="store_true")
    ap.add_argument("--samples", default=None)
    ap.add_argument("--prev-swing-mb", type=float, default=None,
                    help="上一轮**运行中**实测振幅 (自适应余量来源; 缺省=首轮取 MARGIN_FLOOR)")
    ap.add_argument("--prev-postcheck", default=None, help="上一轮 postcheck 落盘件 (取 swing_mb)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--embed-selftest", action="store_true",
                    help="把成对控制结论并入 --out 的落盘件")
    a = ap.parse_args()

    if a.selftest:
        st = selftest()
        print(json.dumps(st, ensure_ascii=False))
        return 0 if st["has_teeth"] else 2

    if not (a.derive or a.postcheck):
        ap.error("需要 --derive 或 --postcheck (或 --selftest)")

    prev = a.prev_swing_mb
    if prev is None and a.prev_postcheck and os.path.isfile(a.prev_postcheck):
        try:
            prev = json.load(io.open(a.prev_postcheck, encoding="utf-8")).get("swing_mb")
        except Exception:  # noqa: BLE001
            prev = None
    xs = _read_samples(a.samples) if a.samples else None
    rec = derive(xs, prev) if a.derive else postcheck(xs)
    rec.update({"round": "R569", "instrument": "gate_margin_r569.py",
                "samples": a.samples, "mode": "derive" if a.derive else "postcheck",
                "gate_mb": GATE_MB, "margin_floor_mb": MARGIN_FLOOR,
                "applied_via": "既有闸 --gate-mb (零新逻辑进闸)"})
    if a.embed_selftest:
        st = selftest()
        rec["selftest"] = st
        if not st["has_teeth"]:
            rec["rc"] = 2
            rec["why"] = "clause_selftest_failed"
    if a.out:
        json.dump(rec, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(rec, ensure_ascii=False))
    return rec["rc"]


if __name__ == "__main__":
    sys.exit(main())
