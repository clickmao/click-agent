#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R619 起手闸余量重派生（协议 §2 步 0 / 前轮候选⑤）—— **余量的唯一来源**。

口径（承 R590 派生版，逐字沿用）:
    MARGIN := clamp(prev_swing_effective, floor=60, cap=CEIL-GATE-floor)
    REQ    = GATE + MARGIN           (GATE = 产品门槛 2650MB)

prev_swing_effective = **上一轮同态在飞窗实测振幅**（r618 run-samples.jsonl）。
本件落盘后被 runner **读取**（不再在脚本里写死字面量）⇒ 单一来源，无第二处可漂移。

判别力成对控制（有牙）由 runner 行使（R618 同形，未改）:
    用内存压制把 MemAvailable 抬进带 `[GATE, REQ)` ⇒ 基础门槛 PASS ∧ 条款 GATE_BLOCKED。
    本件只报带的位置与压制量，**不自我宣称有牙**（防「器具自证」）。

rc: 0 可用 / 2 窗口不可开（fail-closed，非器具缺陷） / 3 输入缺失
"""
import argparse
import io
import json
import os
import sys

GATE_MB = 2650          # 产品门槛（承 R618 GATE_MB）
FLOOR = 60              # 条款下限
CAP_HEADROOM = 60       # 顶棚必须留出的余量


def mem_available_mb():
    with io.open("/proc/meminfo", encoding="utf-8") as fh:
        for ln in fh:
            if ln.startswith("MemAvailable:"):
                return int(ln.split()[1]) // 1024
    raise RuntimeError("MemAvailable 缺失")


def swing_from(path):
    vals = []
    if not os.path.exists(path):
        return None
    for ln in io.open(path, encoding="utf-8", errors="replace"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            d = json.loads(ln)
        except Exception:
            continue
        v = d.get("mem_available_mb")
        if isinstance(v, (int, float)):
            vals.append(int(v))
    if not vals:
        return None
    return {"swing": max(vals) - min(vals), "n": len(vals),
            "min": min(vals), "max": max(vals), "src": path}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prev", required=True, help="上轮 run-samples.jsonl")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    sw = swing_from(args.prev)
    if sw is None:
        print("SYNTH=INPUT_MISSING prev_samples=%s" % args.prev)
        print("rc=3")
        return 3

    ceil3 = [mem_available_mb() for _ in range(3)]
    ceiling = min(ceil3)
    spread = max(ceil3) - min(ceil3)

    cap = ceiling - GATE_MB - CAP_HEADROOM
    margin = max(FLOOR, min(sw["swing"], cap))
    req = GATE_MB + margin
    cap_binding = bool(cap < sw["swing"])
    openable = bool(ceiling >= req)
    band_lo, band_hi = GATE_MB, req
    hog_mb = max(0, ceiling - (band_lo + (band_hi - band_lo) // 2))

    doc = {
        "round": "R619",
        "criterion": "C3 起手闸余量条款（R590 派生版；余量源按 R618 同态在飞窗实测重派生）",
        "clause": "MARGIN := clamp(prev_swing_effective, floor=%d, cap=CEIL-GATE-floor); REQ=GATE+MARGIN" % FLOOR,
        "prev_swing_effective": margin,
        "prev_swing_raw": sw["swing"],
        "prev_swing_source": "r618/logs/run-samples.jsonl (同态在飞窗, n=%d, min=%d, max=%d, swing=%d)"
                             % (sw["n"], sw["min"], sw["max"], sw["swing"]),
        "ceiling_3_samples": ceil3,
        "ceiling_min_of_3": ceiling,
        "pre_sample_spread_mb": spread,
        "spread_clause": "<=50MB else fail-closed（runner 逐次复验）",
        "cap": cap,
        "cap_binding": cap_binding,
        "margin": margin,
        "req": req,
        "gate_mb": GATE_MB,
        "openable": openable,
        "preflight_min_avail_mb": req,
        "paired_control": {
            "exercised_by": "runner（内存压制入带 [GATE, REQ)）",
            "band": [band_lo, band_hi],
            "approx_hog_mb": hog_mb,
            "expect": "基础门槛 PASS ∧ 条款 GATE_BLOCKED",
            "self_claimed_teeth": False,
            "note": "本件不自证有牙；若内存已在带内不可压 ⇒ 如实记「未行使」（R607 同形处置）",
        },
    }
    with io.open(args.out, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")

    print(json.dumps({k: doc[k] for k in ("ceiling_min_of_3", "prev_swing_raw", "margin",
                                          "req", "cap", "cap_binding", "openable")},
                     ensure_ascii=False))
    print("[带] 判别力成对控制带 = [%d, %d) MB，压制量 ≈ %d MB" % (band_lo, band_hi, hog_mb))
    if not openable:
        print("SYNTH=WINDOW_UNOPENABLE ceiling=%d < REQ=%d ⇒ fail-closed（清场后重取，禁降标准强开）"
              % (ceiling, req))
        print("rc=2")
        return 2
    if spread > 50:
        print("SYNTH=CEILING_UNSTABLE spread=%dMB (>50) ⇒ 跨态；本读数仅记录，runner 会逐次复验" % spread)
    print("rc=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
