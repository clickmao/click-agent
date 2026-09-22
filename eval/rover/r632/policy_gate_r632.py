#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R632 · 候选② —— `unreliable_policy` 机检闸（三态 POLICY_ACTIVE + 反事后声明）。

来源与语义逐字对齐 `eval/rover/r507pre/exec_precondition.py` 的 _policy()（R529 J4b）:
  A1 `unreliable_policy` 键存在 ∧ `rule` 非空 ∧ `declared_before_run == true`
  A2 `policy_declared_ts` 可解析 ∧ **prereg 文件自身 mtime >= 该 ts**（时间戳不得事后/虚构）
  A3 该轮**每个窗**的 artifacts.json mtime >= policy_declared_ts（**先声明再跑**；违反 ⇒ 整体拒绝）
  bars B1 本侧(agent*)臂的任何失败一律不得被本规则吞掉 / B2 先声明再跑 / B3 不改历史轮 rc
输出恒含机读行 `POLICY_ACTIVE=<bool> reason=<code> checks=...`（三态；缺键 ⇒ fail-closed 拒绝生效）。

用法:
  python3 eval/rover/r632/policy_gate_r632.py --prereg <p> [--windows-dir <d>] [--json <out>]
  python3 eval/rover/r632/policy_gate_r632.py --selftest        # 正/负控（含"事后声明必拒"注入）
"""
import argparse
import datetime as dt
import io
import json
import os
import shutil
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PD = os.path.join(REPO, "eval/rover/r632")
R631 = os.path.join(REPO, "eval/rover/r631")


def _parse_ts(s):
    if not s:
        return None
    t = str(s).strip().replace("Z", "+00:00")
    try:
        d = dt.datetime.fromisoformat(t)
    except Exception:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d


def check(prereg_path, windows_dir=None):
    out = {"prereg": prereg_path, "checks": {}, "active": False, "reason": None}
    try:
        doc = json.load(io.open(prereg_path, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        out["reason"] = "PREREG_UNREADABLE"
        out["checks"]["read"] = str(e)[:80]
        return out
    pol = doc.get("unreliable_policy")
    if not isinstance(pol, dict) or not pol.get("rule"):
        out["reason"] = "POLICY_MISSING"
        out["checks"]["A1_key_and_rule"] = False
        return out
    out["checks"]["A1_key_and_rule"] = True
    a1b = bool(pol.get("declared_before_run") is True)
    out["checks"]["A1b_declared_before_run"] = a1b
    ts = _parse_ts(pol.get("policy_declared_ts"))
    out["checks"]["A2_ts_parseable"] = ts is not None
    mt = None
    if ts is not None:
        try:
            mt = dt.datetime.fromtimestamp(os.path.getmtime(prereg_path), tz=dt.timezone.utc)
        except Exception:
            mt = None
    out["checks"]["A2_prereg_mtime_ge_ts"] = bool(ts and mt and mt >= ts)
    out["prereg_mtime"] = mt.isoformat() if mt else None
    out["policy_declared_ts"] = ts.isoformat() if ts else None
    wins = []
    if windows_dir and ts and os.path.isdir(windows_dir):
        for w in sorted(os.listdir(windows_dir)):
            ap = os.path.join(windows_dir, w, "artifacts.json")
            if os.path.isfile(ap):
                am = dt.datetime.fromtimestamp(os.path.getmtime(ap), tz=dt.timezone.utc)
                wins.append({"window": w, "artifacts_mtime": am.isoformat(), "ge_ts": bool(am >= ts)})
    out["checks"]["A3_windows_declared_before_run"] = (all(x["ge_ts"] for x in wins) if wins else None)
    out["windows"] = wins
    ok = (out["checks"]["A1_key_and_rule"] and a1b and out["checks"]["A2_ts_parseable"]
          and out["checks"]["A2_prereg_mtime_ge_ts"]
          and out["checks"]["A3_windows_declared_before_run"] is not False)
    out["active"] = bool(ok)
    if ok:
        out["reason"] = "POLICY_ACTIVE"
    elif not a1b:
        out["reason"] = "NOT_DECLARED_BEFORE_RUN"
    elif not out["checks"]["A2_prereg_mtime_ge_ts"]:
        out["reason"] = "TS_AFTER_PREREG_MTIME(post-hoc)"
    elif out["checks"]["A3_windows_declared_before_run"] is False:
        out["reason"] = "RUN_PREDATES_DECLARATION(post-hoc retro)"
    else:
        out["reason"] = "OTHER"
    out["bars"] = {"B1_product_failures_not_swallowed": "由调用方机检（见 nc/close 件）",
                   "B2_declared_before_run": out["checks"]["A3_windows_declared_before_run"] is not False,
                   "B3_no_history_rc_change": "见 D4 历史件 sha256 不变断言"}
    return out


def selftest():
    """控制矩阵: POS=缺键必拒 / NEG=合规必活 / INJ1=ts 晚于 prereg mtime 必拒 / INJ2=窗先于声明必拒。"""
    tmp = tempfile.mkdtemp(prefix="r632pol-")
    rows, rc = [], 0
    try:
        pos = check(os.path.join(R631, "prereg-r631.json"), os.path.join(R631, "evidence/windows"))
        rows.append({"case": "POS_prereg_r631", "expect_reason": "POLICY_MISSING", "got": pos["reason"],
                     "expect_active": False, "active": pos["active"]})
        negp = os.path.join(REPO, "eval/rover/r529/prereg-r529.json")
        neg = check(negp, None)
        rows.append({"case": "NEG_prereg_r529", "expect_reason": "POLICY_ACTIVE", "got": neg["reason"],
                     "expect_active": True, "active": neg["active"]})
        # INJ1: 合规件的 ts 改到未来 ⇒ A2 必红
        d1 = json.load(io.open(negp, encoding="utf-8"))
        d1["unreliable_policy"]["policy_declared_ts"] = (
            dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)).isoformat().replace("+00:00", "Z")
        p1 = os.path.join(tmp, "prereg-future-ts.json")
        json.dump(d1, io.open(p1, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        i1 = check(p1, None)
        rows.append({"case": "INJ1_future_ts", "expect_active": False, "active": i1["active"], "got": i1["reason"]})
        # INJ2: 本轮的策略声明 + R631 既有窗（窗先于声明）⇒ A3 必红（禁事后追溯套用）
        i2 = check(os.path.join(PD, "prereg-r632.json"), os.path.join(R631, "evidence/windows"))
        rows.append({"case": "INJ2_retro_windows", "expect_active": False, "active": i2["active"], "got": i2["reason"],
                     "expect_reason": "RUN_PREDATES_DECLARATION(post-hoc retro)"})
        teeth = (pos["reason"] == "POLICY_MISSING" and pos["active"] is False
                 and neg["reason"] == "POLICY_ACTIVE" and neg["active"] is True
                 and i1["active"] is False and i2["active"] is False)
        rc = 0 if teeth else 2
        res = {"selftest": "policy_gate_r632", "rc": rc, "teeth": bool(teeth), "rows": rows,
               "note": "四态缺一则判据无牙：缺键必拒（fail-closed）/ 合规必活 / 事后 ts 必拒 / 追溯套用既有窗必拒"}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prereg", default=os.path.join(PD, "prereg-r632.json"))
    ap.add_argument("--windows-dir", default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    r = check(a.prereg, a.windows_dir)
    if a.json:
        json.dump(r, io.open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("POLICY_ACTIVE=%s reason=%s checks=%s" % (r["active"], r["reason"], json.dumps(r["checks"], ensure_ascii=False)))
    return 0 if r["active"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
