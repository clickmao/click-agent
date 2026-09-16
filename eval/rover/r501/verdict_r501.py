#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R501 裁决器 v2 —— 判据**逐字**按 prereg_r501.json 的 hypotheses（禁事后改判据）。

与 judge_paraphrase_r499.py 相互独立 = 双仪器（付费量口径只认后者）。

v2 修复（R501 自捕，读写契约不一致）:
  ① 落盘形态: 臂写侧 `turns-<arm>.jsonl` 是**单个 pretty JSON 对象**（含 turns 列表），
     原实现按逐行 JSONL 解析 ⇒ JSONDecodeError。
  ② t8 行定位: 臂遥测的 `local_turn_gate` 行**没有** top-level `msg_sha16`（原实现按该字段匹配
     ⇒ t8rows 恒空 ⇒ H1p/H2 假红）。改用「第 8 条 gate 行」= grid 第 8 轮，并以
     `paraphrase_degrade_remote.kv.msg_sha16 == sha16(t8文本)` 做**交叉校验**（不一致 ⇒ fail-closed rc=2）。

退出码: 0=预注册判据全成立; 1=有证伪; 2=输入缺失/交叉校验失败 (fail-closed)
"""
import argparse
import hashlib
import io
import json
import os
import sys

ARMS = [("C", ""), ("P", "1"), ("P", "2"), ("P", "3")]
H1P_TOKENS = ("mechanical:paraphrase", "gate:paraphrase_no_replayable_prev", "gate:paraphrase_guard_rejected")


def sha16(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def load_any(p):
    """兼容两种落盘形态: ① 逐行 JSONL ② 单对象 pretty JSON（含 turns 列表 ⇒ 返回 turns）。"""
    if not os.path.isfile(p):
        return None
    txt = io.open(p, encoding="utf-8-sig").read()
    try:
        obj = json.loads(txt)
    except Exception:
        return [json.loads(l) for l in txt.splitlines() if l.strip()]
    if isinstance(obj, dict) and isinstance(obj.get("turns"), list):
        return obj["turns"]
    return obj if isinstance(obj, list) else [obj]


def kv_of(r):
    return (r.get("kv") or {}) if isinstance(r, dict) else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="eval/rover/r501")
    ap.add_argument("--out", default="eval/rover/r501/verdict_r501.json")
    a = ap.parse_args()
    d = a.dir

    grid = json.load(io.open(os.path.join(d, "grid/task-p17-code.json"), encoding="utf-8-sig"))
    turns = grid["turns"] if isinstance(grid, dict) and "turns" in grid else grid
    t8 = turns[7]
    t8txt = t8 if isinstance(t8, str) else (t8.get("input") or t8.get("user") or t8.get("text"))
    t8sha = sha16(t8txt)

    res = {"round": "R501", "verdict_device": "verdict_r501.py v2", "t8_text": t8txt,
           "t8_sha16": t8sha, "arms": {}, "verdicts": {}, "reasons": []}
    missing, xcheck_fail = [], []

    for arm_fam, sfx in ARMS:
        base = "%s%s" % (arm_fam, sfx)
        tel = load_any(os.path.join(d, "tel-%s/host.jsonl" % base))
        tv = load_any(os.path.join(d, "turns-%s.jsonl" % base))
        fl = os.path.join(d, "flags-%s.json" % base)
        flags = json.load(io.open(fl, encoding="utf-8-sig")) if os.path.isfile(fl) else None
        if tel is None or flags is None:
            missing.append(base)
            continue
        gates = [r for r in tel if r.get("point") == "local_turn_gate"]
        rej = [r for r in tel if r.get("point") == "local_turn_gate_reject"]
        vio = [r for r in tel if r.get("point") == "gate_prefilter_invariant_violation"]
        deg_all = [r for r in tel if r.get("point") == "paraphrase_degrade_remote"]
        deg_t8 = [r for r in deg_all if kv_of(r).get("msg_sha16") == t8sha]
        # t8 行: 第 8 条 gate 行 (grid 第 8 轮)
        t8row = gates[7] if len(gates) >= 8 else None
        t8kv = kv_of(t8row)
        basis, raw = t8kv.get("basis"), t8kv.get("raw")
        # 交叉校验: 若遥测里出现带 t8sha 的行, 必须落在 t8 行邻域(±2) —— 否则定位可疑
        idx = [i for i, r in enumerate(tel) if kv_of(r).get("msg_sha16") == t8sha]
        if t8row is None:
            xcheck_fail.append("%s: gate 行不足 8 条" % base)
        elif idx:
            near = any(abs(i - tel.index(t8row)) <= 2 for i in idx)
            if not near:
                xcheck_fail.append("%s: t8sha 行远离第 8 条 gate 行" % base)
        # H1p: basis 含 paraphrase 族 token 且不再是 R444 后置否决
        h1p = bool(basis and ("paraphrase" in basis or basis in H1P_TOKENS or raw in H1P_TOKENS)) \
            and "skip_rejected" not in (basis or "")
        # H3: 本地生成仅当 basis==mechanical:paraphrase 且无 degrade 支
        local_gen = (basis == "mechanical:paraphrase") and not deg_t8
        if local_gen:
            remote_t8, t8_mode = 0, "local-generated"
        elif deg_t8:
            remote_t8, t8_mode = 1, "degrade→remote"
        else:
            remote_t8, t8_mode = None, "unreported"
        # H4: t8 答复非空 ∧ 非上一条逐字复读
        rep8 = rep7 = None
        if isinstance(tv, list):
            m8 = [x for x in tv if x.get("turn") == 8]
            m7 = [x for x in tv if x.get("turn") == 7]
            rep8 = m8[0].get("reply") if m8 else None
            rep7 = m7[0].get("reply") if m7 else None
        h4 = bool(rep8) and (rep7 is None or rep8 != rep7) and all(kv_of(r).get("reason") for r in deg_all)
        res["arms"][base] = {
            "paraphrase_flag": (flags or {}).get("local_paraphrase"),
            "gate_rows": len(gates),
            "t8_basis": basis, "t8_raw": raw, "t8_h1p": h1p,
            "t8_mode": t8_mode, "t8_remote_calls": remote_t8,
            "t8_reply_len": len(rep8 or ""), "t8_duplicate_of_prev": (rep8 == rep7),
            "reject_n": len(rej), "violation_n": len(vio),
            "degrade_n": len(deg_all), "degrade_t8_n": len(deg_t8),
            "degrade_reasons": [kv_of(r).get("reason") for r in deg_all],
            "degrade_t8_reasons": [kv_of(r).get("reason") for r in deg_t8],
            "h4_reply_ok": h4,
        }

    if missing:
        print("[致命] 输入缺失 fail-closed: " + ",".join(missing))
        sys.exit(2)
    if xcheck_fail:
        print("[致命] t8 交叉校验失败 fail-closed: " + "; ".join(xcheck_fail))
        sys.exit(2)

    p_arms = sorted(k for k in res["arms"] if k.startswith("P"))
    c = res["arms"]["C"]
    h1p_n = sum(1 for k in p_arms if res["arms"][k]["t8_h1p"])
    h1n_n = sum(1 for k in p_arms if res["arms"][k]["reject_n"] == 0 and res["arms"][k]["violation_n"] == 0)
    local_n = sum(1 for k in p_arms if res["arms"][k]["t8_mode"] == "local-generated")
    deg_n = sum(1 for k in p_arms if res["arms"][k]["t8_mode"] == "degrade→remote")
    h2 = (c["t8_basis"] == "mechanical:nonack→remote" and c["reject_n"] == 0 and c["violation_n"] == 0)
    h4 = all(res["arms"][k]["h4_reply_ok"] for k in p_arms)
    res["verdicts"] = {
        "H1p_reached": "%d/3" % h1p_n, "H1p_pass": h1p_n == 3,
        "H1n_veto_removed": "%d/3" % h1n_n, "H1n_pass": h1n_n == 3,
        "H2_control_pass": bool(h2),
        "H3_local_generated_arms": local_n, "H3_degrade_arms": deg_n,
        "H3_claim": ("本地生成 %d/3" % local_n) if local_n else "**degrade 支 ⇒ 每臂 t8 仍 1 次远端调用 ⇒ 禁宣称改写收益**",
        "H4_reply_and_reasons_ok": bool(h4),
    }
    ok = res["verdicts"]["H1p_pass"] and res["verdicts"]["H1n_pass"] and h2
    res["overall"] = "GREEN" if ok else "RED"
    res["overall_note"] = ("结构面 PASS（后置否决已除、通道到达）∧ 效果面 **不得** 宣称改写收益（degrade 支）"
                           if ok else "结构面或正控不成立 ⇒ 按 prereg falsified_if 处置")
    io.open(a.out, "w", encoding="utf-8", newline="\n").write(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    for k in ["C"] + p_arms:
        v = res["arms"][k]
        print("%-3s flag=%-3s rows=%2d t8_basis=%-28s raw=%-28s mode=%-16s rej=%d vio=%d deg=%d rep_len=%d" %
              (k, v["paraphrase_flag"], v["gate_rows"], v["t8_basis"], v["t8_raw"], v["t8_mode"],
               v["reject_n"], v["violation_n"], v["degrade_n"], v["t8_reply_len"]))
    print("VERDICT=%s H1p=%s H1n=%s H2=%s | H3: %s | H4=%s" %
          (res["overall"], res["verdicts"]["H1p_reached"], res["verdicts"]["H1n_veto_removed"],
           res["verdicts"]["H2_control_pass"], res["verdicts"]["H3_claim"], res["verdicts"]["H4_reply_and_reasons_ok"]))
    print("OUT=" + a.out)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
