#!/usr/bin/env python3
"""R505 器具改版留痕: 判分器 v1→v2（H8 归因覆盖率增强）。

背景（诚实纪律）: 批 A 测完**之后**才发现归因器对「深轮次（tail_messages 只剩 assistant/tool）」
必然未归因 ⇒ H8 红。修法是新增第二阶段「同轮对话延续」归因（可机检、不猜）。
判分器与被测对象的**分离**使这次改版不必重跑: 判分是仓内不可变快照的纯函数。
本脚本: ① 机检 v1/v2 判据读数的影响面（H2/H3/H4/H5/H6/H9/H10/H11 + 用量/质量 须逐位不变, H8 允许变）;
        ② 把新品器哈希与影响面证据钉进预注册（amendments, 保形）。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PRE = os.path.join(HERE, "prereg_r505.json")
WATCH = {"judge_py": os.path.join(HERE, "judge_contrast_r505.py"),
         "attr_py": os.path.join(HERE, "attr_calls_r505.py")}
FROZEN = ["H2", "H3", "H4", "H5", "H6", "H9", "H10", "H11"]


def load(p):
    with open(p, encoding="utf-8-sig") as fh:
        return json.load(fh)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main() -> int:
    ev = os.path.join(HERE, "evidence", "a")
    v1p, v2p = os.path.join(ev, "verdict-r505a-judgev1.json"), os.path.join(ev, "verdict-r505a.json")
    if not (os.path.exists(v1p) and os.path.exists(v2p)):
        print("[致命] 缺 v1/v2 判据产物 ⇒ rc=3")
        return 3
    v1, v2 = load(v1p), load(v2p)
    c1 = {c["id"]: bool(c.get("pass")) for c in v1["criteria"]}
    c2 = {c["id"]: bool(c.get("pass")) for c in v2["criteria"]}
    chk = {k: {"v1": c1.get(k), "v2": c2.get(k)} for k in sorted(set(c1) | set(c2))}
    frozen_ok = all(chk.get(k, {}).get("v1") == chk.get(k, {}).get("v2") for k in FROZEN)
    totals_same = v1["totals"] == v2["totals"]
    table_same = v1["table"] == v2["table"]
    h8_changed = chk.get("H8", {}).get("v1") != chk.get("H8", {}).get("v2")
    rec = {
        "ts_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "v1": {"path": os.path.relpath(v1p, REPO), "rc": v1["rc"], "sha256": sha(v1p)},
        "v2": {"path": os.path.relpath(v2p, REPO), "rc": v2["rc"], "sha256": sha(v2p)},
        "criteria": chk,
        "impact": {"frozen_criteria_unchanged": frozen_ok, "totals_unchanged": totals_same,
                   "table_unchanged": table_same, "h8_changed": h8_changed},
        "reading": ("判分器改版只影响 H8（归因覆盖）; 用量/质量/同输入/同模型/幂等/不可变/反向控制诸项逐位不变"
                    if (frozen_ok and totals_same and table_same and h8_changed)
                    else "改版影响面超出预期 ⇒ 必须重跑, 不得沿用批 A 读数"),
    }
    outp = os.path.join(ev, "judge-amendment-impact.json")
    with open(outp, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(json.dumps(rec["impact"], ensure_ascii=False))
    print("影响面证据 -> %s" % os.path.relpath(outp, REPO))
    if not (frozen_ok and totals_same and table_same):
        print("[致命] 改版影响面超出预期 ⇒ rc=1（批 A 读数作废）")
        return 1

    pre = load(PRE)
    old = {k: pre["files_sha256"].get(k) for k in WATCH}
    new = {k: sha(p) for k, p in WATCH.items()}
    pre["files_sha256"].update(new)
    pre.setdefault("amendments", []).append({
        "round": "R505", "kind": "instrument_revision", "ts_utc": rec["ts_utc"],
        "scope": "判分器 v1→v2: 新增「同轮对话延续」归因阶段（H8 覆盖）",
        "files": {k: {"old": old[k], "new": new[k]} for k in WATCH},
        "impact_check": os.path.relpath(outp, REPO),
        "impact_reading": rec["reading"],
        "evidence_reuse": "批 A 复用（判分=快照纯函数; 两侧 LLM 流量未变, 见 impact_check 的 totals/table 逐位相同）",
    })
    with open(PRE, "w", encoding="utf-8") as fh:
        json.dump(pre, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print("预注册已改版留痕: %s" % os.path.relpath(PRE, REPO))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())