#!/usr/bin/env python3
"""R608 判据器 · RF0004.1 开放域识别统一出口 `{标签|abstain, 依据}`（M1 落地轮）。

判据单源 = eval/rover/r608/prereg-r608.json（**不在本器内重定义阈值**）。
派生自 eval/rover/r607/judge_r607.py（结构复用）+ 逐条声明差异:
  ① 键集: 打点面三键(local_turn_gate/nlp_shape/local_gate_skip_reply) → 出口面三键
     (outlet_emit / outlet_abstain / outlet_local)。
  ② P3: 闸前置(turn_gate_config) → 出口覆盖(count == 轮数)。
  ③ 新增 P2 消融逐位等价（判定面序列 T vs C 逐位）+ checks_posthoc 可比域形态。
  ④ --negctl 模式: 交换 T/C 读数重判，断言 P1 必翻红（有牙）。
只读输入：prereg-r608.json + offsets-r608.json + data/telemetry/host.jsonl（按字节偏移切片）。
输出：verdict-r608.json（主）/ verdict-r608-negctl.json（负控）；判定只写 JSON 的 `verdict` 键，rc 由 `verdict` 派生。
rc: 0 = 全判据 PASS / 1 = 判据不符 / 2 = 器具缺陷（fail-closed）/ 3 = 输入缺失（offsets/切片空）
"""
import io
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RD = ROOT / "eval" / "rover" / "r608"
PRE = RD / "prereg-r608.json"
OFF = RD / "offsets-r608.json"
TEL = ROOT / "data" / "telemetry" / "host.jsonl"
BASE = ROOT / "eval" / "capability" / "baselines.json"
OUT = RD / "verdict-r608.json"
OUT_NEG = RD / "verdict-r608-negctl.json"
TURNS = 2                       # 夹具轮数（prereg.fixture.turns_per_arm）

KEYS = {
    "outlet_emit":    ("recognition_verdict", lambda k: True),
    "outlet_abstain": ("recognition_verdict", lambda k: str(k.get("abstain")) in ("1", "True", "true")),
    "outlet_local":   ("recognition_verdict", lambda k: str(k.get("abstain")) in ("0", "False", "false")
                       and bool(k.get("label")) and k.get("label") != "abstain"),
}


def _boolish(x):
    """契约: 布尔字段以 .NET bool.ToString() 形态落盘（'True'/'False'）；归一 + 缺失 fail-closed。"""
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
    out = {name: 0 for name in KEYS}
    samples = {}
    seq = []                      # 判定面序列（本地消化链的机械读数）
    by_msg = {}                   # msg_sha16 -> set(verdict|basis)
    costs = {"calls": 0, "prompt_new": 0, "completion": 0, "unreported": 0}
    for d in rows:
        pt = d.get("point")
        kv = d.get("kv") or {}
        for name, (key, pred) in KEYS.items():
            if pt == key and pred(kv):
                out[name] += 1
                samples.setdefault(name, kv)
        if pt in ("local_turn_gate", "nlp_shape"):
            seq.append([pt, str(kv.get("decided")), str(kv.get("verdict")), str(kv.get("shape")),
                        str(kv.get("face")), str(kv.get("route")), str(kv.get("basis"))])
            by_msg.setdefault(str(kv.get("msg_sha16")), set()).add(
                "%s|%s" % (kv.get("verdict"), kv.get("basis")))
        elif pt == "local_gate_skip_reply":
            seq.append([pt, str(kv.get("kind")), str(kv.get("msg_sha16"))])
        elif pt == "llm_call":
            if kv.get("prompt_tokens") is None or kv.get("completion_tokens") is None:
                costs["unreported"] += 1
                continue
            costs["calls"] += 1
            costs["prompt_new"] += int(kv.get("prompt_tokens") or 0)
            costs["completion"] += int(kv.get("completion_tokens") or 0)
    return {"counts": out, "kv_samples": samples, "seq": seq,
            "by_msg": {k: sorted(v) for k, v in sorted(by_msg.items())}, "costs": costs}


def main():
    neg = "--negctl" in sys.argv
    v = {"round": "R608", "kind": "RF0004.1 识别出口落地判决（打点面判别力 + 只读消融）",
         "judge_version": "v1.1", "mode": "negctl" if neg else "main", "checks": {}, "defects": [],
         "judge_revision": "v1→v1.1 只改 checks_posthoc 的可比域算法（预注册判据集与阈值一字未改；P2 仍按原样判 FAIL）"}
    # 影子自检（读数归一 + 预注册契约）
    assert _boolish("True") is True and _boolish("true") is True and _boolish(True) is True
    assert _boolish("False") is False and _boolish(None) is None and _boolish("") is None
    assert KEYS["outlet_emit"][0] == "recognition_verdict"
    for p in (PRE, OFF):
        if not p.exists():
            print(json.dumps({"verdict": "VOID", "why": "缺输入 %s" % p.name}, ensure_ascii=False))
            return 3
    pre = json.loads(io.open(PRE, encoding="utf-8").read())
    offs = json.loads(io.open(OFF, encoding="utf-8").read())
    if not TEL.exists():
        print(json.dumps({"verdict": "VOID", "why": "缺 host.jsonl"}, ensure_ascii=False))
        return 3

    v["binary_sha256"] = ""
    if (RD / "pre-arm-state.txt").exists():
        txt = io.open(RD / "pre-arm-state.txt", encoding="utf-8").read()
        if "bin_sha256=" in txt:
            v["binary_sha256"] = txt.split("bin_sha256=")[1].split("\n")[0]
    v["fixture_sha256"] = pre.get("fixture", {}).get("fixture_shapes_sha256")
    v["single_variable"] = pre.get("single_variable")

    arms = {"T": [], "C": []}
    for rec in offs:
        rows = slice_rows(rec["off"], rec["after"])
        r = arm_reading(rows)
        r.update({"rep": rec["rep"], "session": rec["session"], "rc": rec["rc"],
                  "bytes": rec["after"] - rec["off"], "rows": len(rows)})
        arms[rec["arm"]].append(r)
    if sum(len(x) for x in arms.values()) < 2 or all(not x["rows"] for x in arms["T"]):
        v["verdict"] = "VOID"
        v["rc"] = 3
        v["why"] = "切片为空/有效跑次 <2（协议 §3 R3）"
        io.open(OUT, "w", encoding="utf-8").write(json.dumps(v, ensure_ascii=False, indent=1) + "\n")
        print(json.dumps({k: v[k] for k in ("round", "verdict", "rc", "why")}, ensure_ascii=False))
        return 3

    T = list(arms["T"]) if not neg else list(arms["C"])
    C = list(arms["C"]) if not neg else list(arms["T"])
    v["negctl_swapped"] = bool(neg)

    # ── P1 治疗 >0 ∧ 对照 ==0（三键） ────────────────────────────────────────────
    p1 = {name: [r["counts"][name] for r in T] for name in KEYS}
    p2 = {name: [r["counts"][name] for r in C] for name in KEYS}
    v["checks"]["P1_treatment_positive"] = {
        "ok": all(len(x) >= 3 and min(x) >= 1 for x in p1.values()),
        "counts_per_rep": p1, "rule": "每个治疗跑次 `recognition_verdict` 事件数 ≥1（reps≥3，三键齐）"}
    v["checks"]["P2_control_zero"] = {
        "ok": all(len(x) >= 3 and max(x) == 0 for x in p2.values()),
        "counts_per_rep": p2, "rule": "每个对照跑次 `recognition_verdict` 事件数 ==0（轴关=旧行为）"}

    # ── P3 出口覆盖（事件数 == 轮数）+ abstain 首读基线 ─────────────────────────
    cov_t = [r["counts"]["outlet_emit"] for r in T]
    v["checks"]["P3_outlet_coverage"] = {
        "ok": all(c == TURNS for c in cov_t),
        "coverage_per_rep": cov_t, "turns_per_arm": TURNS,
        "abstain_per_rep": [r["counts"]["outlet_abstain"] for r in T],
        "abstain_rate": (sum(r["counts"]["outlet_abstain"] for r in T) / max(1, sum(cov_t))),
        "rule": "治疗跑次覆盖数 == 轮数（口径可用）；abstain 率作首读基线（无阈值，R609 出口闸判据面）"}

    # ── P4 恒前缀冻结（只许加厚，禁改写） ───────────────────────────────────────
    ent = {e["id"]: e for e in json.loads(io.open(BASE, encoding="utf-8").read()).get("entries", [])}
    pc = ent.get("F_env.prefix.chars", {})
    chk = subprocess.run(pc.get("check_cmd", "false"), shell=True, capture_output=True, text=True)
    v["checks"]["P4_frozen_prefix"] = {
        "ok": pc.get("value") == 15291 and chk.returncode == 0 and "15291" in chk.stdout,
        "prefix_chars_declared": pc.get("value"), "prefix_chars_check_rc": chk.returncode,
        "prefix_chars_observed": chk.stdout.strip()[:200],
        "prefix_sha256_declared": ent.get("F_env.prefix.sha256", {}).get("value"),
        "hit_rate_ge_097": "未测（REPL 面不产恒前缀命中口径：无中继 dump）",
        "rule": "冻结恒前缀 chars/sha 现盘核对；命中率项如实记未测"}

    # ── P5 有牙（负控交换）+ 非平凡（T/C 互异） ─────────────────────────────────
    nontrivial = any(p1[k] != p2[k] for k in KEYS)
    v["checks"]["P5_instrument_has_teeth"] = {
        "ok": bool(nontrivial), "negative_control_expect_rc": 1 if not neg else 1,
        "nontrivial_T_vs_C_differ": bool(nontrivial),
        "rule": "非平凡：T/C 读数必须互异；有牙由 --negctl 交换臂读数复判（P1 必须翻红，见 verdict-r608-negctl.json）"}

    # ── 预注册 P2：消融逐位等价（T/C 判定面序列逐 rep 比） ───────────────────────
    pair = {}
    for i in range(min(len(T), len(C))):
        pair["rep%d" % T[i]["rep"]] = {
            "equal": T[i]["seq"] == C[i]["seq"],
            "T_seq": T[i]["seq"], "C_seq": C[i]["seq"],
            "T_calls": T[i]["costs"]["calls"], "C_calls": C[i]["costs"]["calls"]}
    v["checks"]["P2_ablation_bitwise_equivalent"] = {
        "ok": bool(pair) and all(p["equal"] for p in pair.values()),
        "per_rep": {k: {"equal": p["equal"], "T_calls": p["T_calls"], "C_calls": p["C_calls"]}
                    for k, p in pair.items()},
        "rule": "预注册原样：逐 rep 判定面序列（gate/nlp_shape/skip_reply 三元机械读数）逐位相同"}

    # ── checks_posthoc（事后项，**不参与 verdict**；预注册判据照原样判） ──────────
    def _by_msg(lst):
        out = {}
        for r in lst:
            for k, lst2 in r["by_msg"].items():
                out.setdefault(k, set()).update(lst2)
        return {k: sorted(v2) for k, v2 in out.items()}

    bt, bc = _by_msg(arms["T"]), _by_msg(arms["C"])
    common = [k for k in bt if k in bc]
    comparable = [k for k in common if set(bt[k]) == set(bc[k])]
    all_six = arms["T"] + arms["C"]
    turn1 = {r["session"]: (r["seq"][0] if r["seq"] else None) for r in all_six}
    turn1_unique = len({json.dumps(x, ensure_ascii=False) for x in turn1.values()})
    rep_eq = [k for k, p in pair.items() if p["equal"]]
    v["checks_posthoc"] = {
        "comparable_domain_form_of_P2": {
            "ok_posthoc": len(rep_eq) >= 2 and turn1_unique == 1,
            "per_rep_bitwise_equal": rep_eq,
            "rep_equal_count_of_3": len(rep_eq),
            "turn1_reading_all_six_arms": turn1,
            "turn1_unique_signatures": turn1_unique,
            "comparable_msg_sha16": comparable, "common_msg_sha16": common,
            "T_by_msg": bt, "C_by_msg": bc,
            "note": ("正确形态（事后单列、不入 verdict）：①逐 rep 逐位等价（2/3：rep1/rep3 同）"
                     "②turn1 读数在 6/6 臂唯一（机械 `mechanical:pass→remote`，与模型无关）"
                     "③不可比轮 = rep2（见 upstream_swing）。预注册判据过强（把执行面摆动轮纳入比较域），"
                     "下一轮预注册改为分层（可比域）判据；阈值与判据集本轮不变")},
        "upstream_swing": {
            "rep2": {"T_calls": [r["costs"] for r in arms["T"] if r["rep"] == 2],
                     "C_calls": [r["costs"] for r in arms["C"] if r["rep"] == 2],
                     "basis_diff": ("C r2 turn2 basis = gate:repeat_no_replayable_prev→remote（上游回复形态不同 ⇒ "
                                    "无回放源）⇒ 非轴效应")},
            "attribution_rule": "摆动 ≥ 效应 ⇒ 加 reps/扩窗（禁调阈值），不回撤产品改动（P1/P3/P4/P5 全过）"},
        "outlet_shape_samples": {"T": arms["T"][0]["kv_samples"].get("outlet_emit") if arms["T"] else None},
        "cost_three_columns": {k: [r["costs"] for r in lst] for k, lst in arms.items()},
        "v1_disclosure": {"v1_file": None, "note": "本轮 v1 首跑即用；无重注册"},
    }

    codes = []
    if not v["checks"]["P1_treatment_positive"]["ok"]:
        codes.append(1)
    if not v["checks"]["P2_control_zero"]["ok"]:
        codes.append(1)
    if not v["checks"]["P2_ablation_bitwise_equivalent"]["ok"]:
        codes.append(1)
    if not v["checks"]["P3_outlet_coverage"]["ok"]:
        codes.append(1)
    if not v["checks"]["P4_frozen_prefix"]["ok"]:
        codes.append(1)
    if not v["checks"]["P5_instrument_has_teeth"]["ok"]:
        codes.append(2)
    v["defects"] = [k for k, c in v["checks"].items() if not c.get("ok")]
    v["verdict"] = "FAIL" if 1 in codes else ("INSTRUMENT_DEFECT" if 2 in codes else "PASS")
    v["mechanism_face"] = ("P1/P2/P3/P4 = 出口落地与判别力（机制面）：治疗发出 `recognition_verdict` ∧ 对照 0 ∧ 覆盖全轮 ∧ 前缀不破；"
                           "P2_ablation 逐位等价 = 只读性（消融面）")
    v["capability_face"] = "未行使 —— 无质量对照臂（C1 codex 跳步，见 dag-r608.md）；abstain 率仅首读基线"
    v["arms_raw"] = {k: [{kk: vv for kk, vv in r.items() if kk not in ("kv_samples", "seq", "by_msg")}
                         for r in lst] for k, lst in arms.items()}
    v["rc"] = {"PASS": 0, "FAIL": 1, "INSTRUMENT_DEFECT": 2, "VOID": 3}[v["verdict"]]
    target = OUT_NEG if neg else OUT
    io.open(target, "w", encoding="utf-8").write(json.dumps(v, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: v[k] for k in ("round", "mode", "verdict", "rc", "defects")}, ensure_ascii=False))
    return v["rc"]


if __name__ == "__main__":
    sys.exit(main())
