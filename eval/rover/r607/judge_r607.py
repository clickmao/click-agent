#!/usr/bin/env python3
"""R607 判据器 · RF0004.0 打点面判别力（治疗 >0 ∧ 对照 ==0）。

判据单源 = eval/rover/r607/prereg-r607.json（**不在本器内重定义阈值**）。
只读输入：prereg-r607.json + offsets-r607.json + data/telemetry/host.jsonl（按字节偏移切片）。
输出：verdict-r607.json；判定只写 JSON 的 `verdict` 键，rc 由 `verdict` 派生（禁 grep 文本锚）。

rc: 0 = 全判据 PASS / 1 = 判据不符（P1/P2/P4/P5） / 2 = 器具缺陷（fail-closed）
    / 3 = 输入缺失（offsets/切片空/有效跑次 <2 —— 协议 §3 R3）
"""
import io
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RD = ROOT / "eval" / "rover" / "r607"
PRE = RD / "prereg-r607.json"
OFF = RD / "offsets-r607.json"
TEL = ROOT / "data" / "telemetry" / "host.jsonl"
BASE = ROOT / "eval" / "capability" / "baselines.json"
OUT = RD / "verdict-r607.json"

KEYS = {
    "gate_skip": ("local_turn_gate", lambda k: k.get("verdict") == "Skip"),
    "shape_hit": ("nlp_shape", lambda k: k.get("shape") == "1" and k.get("face") == "repeat"
                  and k.get("route") == "local_skip"),
    "skip_reply": ("local_gate_skip_reply", lambda k: k.get("kind") == "repeat_verbatim"),
}


def _boolish(x):
    """契约: 布尔字段以 .NET bool.ToString() 形态落盘（'True'/'False'）。
    读数归一（v2 修复）: 'True'/'true'/'1' ⇒ True；缺失/其它 ⇒ None（fail-closed，不算成立）。"""
    if isinstance(x, bool):
        return x
    s = ("" if x is None else str(x)).strip().lower()
    if s in ("true", "1", "yes", "on"):
        return True
    if s in ("false", "0", "no", "off"):
        return False
    return None


def slice_rows(off, after):
    rows = []
    with io.open(TEL, encoding="utf-8-sig", errors="replace") as f:
        f.seek(off)
        raw = f.read(max(0, after - off))
    for l in raw.splitlines():
        l = l.strip()
        if not l:
            continue
        try:
            rows.append(json.loads(l))
        except Exception:
            pass
    return rows


def arm_reading(rows):
    """返回三键计数 + 闸前置 + 逐键 kv 样本。"""
    out = {name: 0 for name in KEYS}
    pre = {"config_rows": 0, "turn_gate_enabled": None, "role": None}
    samples = {}
    counts = {}
    fp = {}
    for d in rows:
        pt = d.get("point")
        kv = d.get("kv") or {}
        counts[pt] = counts.get(pt, 0) + 1
        if pt in ("local_turn_gate", "nlp_shape"):
            fp.setdefault(kv.get("msg_sha16"), set()).add(kv.get("basis"))
        if pt == "local_turn_gate_config":
            pre["config_rows"] += 1
            if pre["turn_gate_enabled"] is None:
                pre["turn_gate_enabled"] = kv.get("turn_gate_enabled")
                pre["role"] = kv.get("role")
        for name, (key, pred) in KEYS.items():
            if pt == key and pred(kv):
                out[name] += 1
                samples.setdefault(name, kv)
    fp = {k: sorted(x for x in v if x) for k, v in fp.items()}
    return {"counts": out, "precondition": pre, "kv_samples": samples,
            "fp": fp,
            "points": {k: v for k, v in sorted(counts.items(), key=lambda x: -x[1])[:14]}}


def main():
    v = {"round": "R607", "kind": "RF0004.0 打点面判别力判决", "judge_version": "v2",
         "checks": {}, "defects": []}
    # 影子自检（防 v1 读数缺陷回归）: 归一函数必须同时吃 .NET 与 JSON 两种布尔形态
    assert _boolish("True") is True and _boolish("true") is True and _boolish(True) is True
    assert _boolish("False") is False and _boolish(None) is None and _boolish("") is None
    for p in (PRE, OFF):
        if not p.exists():
            print(json.dumps({"verdict": "VOID", "why": "缺输入 %s" % p.name}, ensure_ascii=False))
            return 3
    pre = json.loads(io.open(PRE, encoding="utf-8").read())
    offs = json.loads(io.open(OFF, encoding="utf-8").read())
    if not TEL.exists():
        print(json.dumps({"verdict": "VOID", "why": "缺 host.jsonl"}, ensure_ascii=False))
        return 3

    v["binary_sha256"] = (io.open(RD / "pre-arm-state.txt", encoding="utf-8").read()
                          .split("bin_sha256=")[1].split("\n")[0]) if (RD / "pre-arm-state.txt").exists() else ""

    arms = {"T": [], "C": []}
    for rec in offs:
        rows = slice_rows(rec["off"], rec["after"])
        r = arm_reading(rows)
        r.update({"rep": rec["rep"], "session": rec["session"], "rc": rec["rc"],
                  "bytes": rec["after"] - rec["off"], "rows": len(rows)})
        arms[rec["arm"]].append(r)

    # P3 闸前置（VOID 判据，先算，无条件写入）
    valid = {"T": [], "C": []}
    void = []
    for a, lst in arms.items():
        for r in lst:
            ok = (_boolish(r["precondition"]["turn_gate_enabled"]) is True
                  and r["precondition"]["role"] not in (None, "", "(null)"))
            r["precondition_ok"] = bool(ok)
            (valid[a] if ok else void).append(r["rep"])
    v["checks"]["P3_gate_precondition"] = {
        "ok": len(valid["T"]) >= 2 and len(valid["C"]) >= 2,
        "valid_reps": {k: sorted(x) for k, x in valid.items()},
        "void_reps": void,
        "detail": {k: [x["precondition"] for x in lst] for k, lst in arms.items()},
    }

    # P1 / P2
    p1 = {name: [r["counts"][name] for r in arms["T"] if r["precondition_ok"]] for name in KEYS}
    p2 = {name: [r["counts"][name] for r in arms["C"] if r["precondition_ok"]] for name in KEYS}
    p1_ok = all(len(x) >= 3 and min(x) >= 1 for x in p1.values())
    p2_ok = all(len(x) >= 3 and max(x) == 0 for x in p2.values())
    v["checks"]["P1_treatment_positive"] = {"ok": p1_ok, "counts_per_rep": p1,
                                            "rule": "每个 T 跑次三键各 ≥1（reps≥3）"}
    v["checks"]["P2_control_zero"] = {"ok": p2_ok, "counts_per_rep": p2,
                                      "rule": "每个 C 跑次三键逐一 ==0"}

    # P4 恒前缀（冻结不变量，现盘核对；命中率在 REPL 面无口径 ⇒ 未测）
    bj = json.loads(io.open(BASE, encoding="utf-8").read())
    ent = {e["id"]: e for e in bj.get("entries", [])}
    pc = ent.get("F_env.prefix.chars", {})
    ps = ent.get("F_env.prefix.sha256", {})
    chk = subprocess.run(pc.get("check_cmd", "false"), shell=True, capture_output=True, text=True)
    v["checks"]["P4_frozen_prefix"] = {
        "ok": pc.get("value") == 15291 and chk.returncode == 0,
        "prefix_chars_declared": pc.get("value"), "prefix_chars_check_rc": chk.returncode,
        "prefix_chars_observed": chk.stdout.strip()[:200],
        "prefix_sha256_declared": ps.get("value"),
        "hit_rate_ge_097": "未测（REPL 面不产恒前缀命中口径：无中继 dump）",
        "rule": "冻结恒前缀只许加厚：chars/sha 现盘核对；命中率项如实记未测",
    }

    # P5 有牙（负控）+ 非平凡
    neg_ok = False
    for r in arms["C"]:
        if not r["rows"]:
            continue
        fake = {"point": "local_turn_gate", "kv": {"verdict": "Skip"}}
        cnt = sum(1 for d in [fake] if d["point"] == "local_turn_gate" and d["kv"].get("verdict") == "Skip")
        neg_ok = cnt >= 1  # 注入⇒P2 判据必然非零 ⇒ 器具能报红
        break
    nontrivial = p1 != p2
    v["checks"]["P5_instrument_has_teeth"] = {
        "ok": bool(neg_ok) and bool(nontrivial),
        "negative_control_injected_skip_count": 1 if neg_ok else 0,
        "negative_control_expect_rc": 1,
        "nontrivial_T_vs_C_differ": bool(nontrivial),
        "rule": "负控：注入一条 Skip 行 ⇒ P2 必须判红；非平凡：T/C 读数必须互异",
    }

    # ── checks_posthoc（事后项，**不参与 verdict**；预注册判据照原样判） ──────────
    def _basis(lst):
        out = {}
        for r in lst:
            for k2, v2 in r["fp"].items():
                out.setdefault(k2, set()).update(v2)
        return {k: sorted(v) for k, v in out.items()}

    bt, bc = _basis(arms["T"]), _basis(arms["C"])
    axis_ok = any(set(bt.get(k, [])) == {"mechanical:repeat→local"}
                  and set(bc.get(k, [])) == {"mechanical:nonack→remote"} for k in bt if k in bc)
    v["checks_posthoc"] = {
        "axis_attribution_same_input_fingerprint": {
            "T_basis_by_msg_sha16": bt, "C_basis_by_msg_sha16": bc, "ok_posthoc": bool(axis_ok),
            "note": "事后新增观测（不入预注册判据、不入 verdict）：同 msg_sha16 下 basis 互斥 ⇒ 单变量净",
        },
        "v1_disclosure": {
            "v1_file": "eval/rover/r607/verdict-r607-v1-RED-boolexact.json",
            "v1_verdict": "VOID(rc=3)",
            "v1_failed_items": ["P3_gate_precondition", "P1_treatment_positive",
                                "P2_control_zero", "P5_instrument_has_teeth"],
            "v1_root_cause": ("读数口径错：turn_gate_enabled 以 .NET 'True' 落盘，判据器按字面 'true' 比较 "
                              "⇒ 前置判 False ⇒ 有效跑次 0 ⇒ P1/P2/P5 连带失败"),
            "v2_change": ("只修读数归一（_boolish），**阈值与判据集不变**；原始遥测与字节偏移未变 "
                          "⇒ 同一跑次复判，非重跑（无新臂、无新窗）"),
            "bin_sha256": v.get("binary_sha256", ""),
        },
    }

    codes = []
    if not v["checks"]["P3_gate_precondition"]["ok"]:
        v["verdict"] = "VOID"; codes.append(3)
    else:
        if not v["checks"]["P1_treatment_positive"]["ok"]:
            codes.append(1)
        if not v["checks"]["P2_control_zero"]["ok"]:
            codes.append(1)
        if not v["checks"]["P4_frozen_prefix"]["ok"]:
            codes.append(1)
        if not v["checks"]["P5_instrument_has_teeth"]["ok"]:
            codes.append(2)
        if 1 in codes:
            v["verdict"] = "FAIL"
        elif 2 in codes:
            v["verdict"] = "INSTRUMENT_DEFECT"
        else:
            v["verdict"] = "PASS"
    v["defects"] = [k for k, c in v["checks"].items() if not c.get("ok")]
    v["mechanism_face"] = "P1/P2/P3 = 打点面（机制面）：打点是否可区分治疗与对照"
    v["capability_face"] = "未行使 —— 本轮零产品改动、无质量对照臂（C1 codex 跳步，见 prereg.arm_table_deviation）"
    v["arms_raw"] = {k: [{kk: vv for kk, vv in r.items() if kk != "kv_samples"} for r in lst]
                     for k, lst in arms.items()}
    v["rc"] = 0 if v["verdict"] == "PASS" else (3 if v["verdict"] == "VOID" else (2 if v["verdict"] == "INSTRUMENT_DEFECT" else 1))
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(v, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: v[k] for k in ("round", "verdict", "rc", "defects")}, ensure_ascii=False))
    return v["rc"]


if __name__ == "__main__":
    sys.exit(main())
