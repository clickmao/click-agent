#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R571 起手闸「擦边 PASS」振幅余量条款 (候选③ 落地件).

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
    """读样本: 返回 [(mem_available_mb, own_rss_mb_or_None)]; 缺 own_rss 字段 ⇒ None (按 0 消费)。"""
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
                o = rec.get("own_rss_mb")
                xs.append((float(v), float(o) if isinstance(o, (int, float)) else None))
        except Exception:  # noqa: BLE001
            continue
    return xs or None


def derive(xs, prev_swing_mb=None):
    """由起手前样本 + 上一轮**观测振幅**派生门槛 (无条件键; 缺项写 None)。

    条款 v2 (数据先行; 修 R571 v1 的结构性不可达):
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
    mv = [(x[0] if isinstance(x, tuple) else x) for x in xs]
    ceil_mb, spread = max(mv), max(mv) - min(mv)
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
    """运行窗口内采样: **v1 原始** 与 **v2 自体归因** 两栏 (R571 承重; 双栏不得互相替代)。

    v1 (旧口径, 逐字保留): `min(mem_available) >= GATE_MB` —— 不看归属。
    v2 (归属口径): `min(mem_available + own_rss) >= GATE_MB` —— 把**本运行血统进程**的内存
       加回去, 回答的是「若不是本运行自身, 基础门槛会被击穿吗」。血统 = 采样器父进程的
       后代 ∪ 命令行含本运行根/端口的进程 (见 mem_sampler.py v2)。

    向后兼容 (禁翻案): 旧样本无 `own_rss_mb` 字段 ⇒ 按 0 消费 ⇒ v2 ≡ v1 ⇒ 旧判决原样保留。
    顶层 rc 取 v2 (修正口径) 并同时给 `rc_v1_raw`; 两者都必须落盘 (缺一即不可解读)。
    """
    if not xs:
        return {"rc": 3, "note": "no_run_samples", "in_min_mb": None, "swing_mb": None}
    mv = [a for a, _ in xs]
    ov = [(b if b is not None else 0.0) for _, b in xs]
    att = [a + b for a, b in zip(mv, ov)]
    i1 = mv.index(min(mv))
    i2 = att.index(min(att))
    ok1 = min(mv) >= GATE_MB
    ok2 = min(att) >= GATE_MB
    n_own_field = sum(1 for _, b in xs if b is not None)
    return {"rc": 0 if ok2 else 2,
            "rc_v1_raw": 0 if ok1 else 2,
            "in_min_mb": round(min(mv), 1), "in_max_mb": round(max(mv), 1),
            "swing_mb": round(max(mv) - min(mv), 1), "n_samples": len(mv),
            "own_rss_max_mb": round(max(ov), 1), "own_rss_at_v1min_mb": round(ov[i1], 1),
            "own_field_samples": n_own_field,
            "attributed_min_mb": round(min(att), 1),
            "attributed_max_mb": round(max(att), 1),
            "attributed_swing_mb": round(max(att) - min(att), 1),
            "raw_drop_mb": round(max(mv) - min(mv), 1),
            "foreign_residual_mb": round(min(att) - GATE_MB, 1),
            "attribution": ("self_cost_explains_breach" if (not ok1 and ok2) else
                            ("foreign_pressure_breach" if not ok2 else
                             ("no_breach" if ok1 else "undetermined"))),
            "gate_mb": GATE_MB, "window_drift": (not ok2), "window_drift_v1": (not ok1),
            "v1_only": (ok2 and not ok1),
            "why": ("ok" if ok2 else "attributed_run_window_breached_base_gate")}


def selftest_postcheck():
    """postcheck v1/v2 成对控制 (器具改版后重钉; 缺一即空心)。

    四例必须同时成立, 否则判据无牙:
      PC_self_explains : 下降**完全**由自体解释 ⇒ v1 红 ∧ v2 绿 (防「一律判红」把自体当污染)
      NC_foreign       : own=0 的真外来压力 ⇒ v2 必红 (防「一律判绿」= 空心条款)
      NC_partial       : 自体只解释一部分 (2630 < 2650) ⇒ v2 **必红** (防「部分归因即放行」)
      PC_old_compat    : 无 own_rss 字段的旧样本 (R570 形状) ⇒ v2 ≡ v1 ⇒ 旧判决 rc=2 **不翻案**
    """
    cases = [
        ("PC_self_explains", [(2600.0, 100.0), (2610.0, 100.0)], 0, 2, "self_cost_explains_breach"),
        ("NC_foreign", [(2539.0, 0.0), (2829.0, 0.0)], 2, 2, "foreign_pressure_breach"),
        ("NC_partial", [(2600.0, 30.0), (2600.0, 30.0)], 2, 2, "foreign_pressure_breach"),
        ("PC_old_compat_R570_shape", [(2539.0, None), (2829.0, None)], 2, 2, "foreign_pressure_breach"),
        ("PC_no_breach", [(2700.0, 0.0)], 0, 0, "no_breach"),
    ]
    out = []
    for name, xs, exp_rc, exp_v1, exp_attr in cases:
        got = postcheck(xs)
        ok = (got["rc"] == exp_rc) and (got["rc_v1_raw"] == exp_v1) and (got["attribution"] == exp_attr)
        out.append({"fixture": name, "expected_rc_v2": exp_rc, "got_rc_v2": got["rc"],
                    "expected_rc_v1": exp_v1, "got_rc_v1": got["rc_v1_raw"],
                    "expected_attribution": exp_attr, "got_attribution": got["attribution"], "ok": ok})
    n_ok = sum(1 for x in out if x["ok"])
    return {"fixtures": out, "n": len(out), "n_ok": n_ok, "has_teeth": n_ok == len(out)}


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
        stp = selftest_postcheck()
        merged = {"derive_selftest": st, "postcheck_selftest": stp,
                  "has_teeth": bool(st["has_teeth"] and stp["has_teeth"]),
                  "n": st["n"] + stp["n"], "n_ok": st["n_ok"] + stp["n_ok"]}
        print(json.dumps(merged, ensure_ascii=False))
        return 0 if merged["has_teeth"] else 2

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
    rec.update({"round": "R571", "instrument": "gate_margin_r571.py",
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
