#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R590 候选②：目标形态（契约块内**过度转义** = 双反斜杠 + n）在 12 窗 × 36 产品跑次上的出现率
与「整族塌陷」「交付缺席」的相关性。**只读 / 零写入 / 零产品改动 / 零远端。**

形态定义（预注册 `eval/rover/r590/prereg-r590.json` C1，逐字）：契约块（`{"schema_version"` 起的
第一段平衡 `{...}`）内出现「双反斜杠 + 字母 n」。派生自 R589 C8 字符级最小化复现定位的元素
（最小删除集 = `plan` 数组元素，其 `args.cmd` 内含该形态）——**非本轮新造**。

读法契约（禁重写第二份）：
- 契约块切分 `contract_span` 直接 **import** R589 器具（`eval/rover/r589/charlevel_bisect_r589.py`），
  保证与已入册读数同口径；其文件 sha 记入输出（口径可追到档）。
- 逐例结果 = `<runs>/<round>/<win>/<arm>/g1/cases.txt`（与 R589 并池器同契约）。
- 族 = case id 的 `#` 前缀。
- 交付缺席 = `<g1>/work` 子树下文件数为 0（与 R588 census 同口径）。

器具自捕纪律：任何成对控制不翻面 ⇒ 判 `has_teeth=false` 并 rc=2（判据不可用），首跑读数留档不翻案。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
import re
import sys

REPO = "/home/agentuser/AgentFramework"
RUNS = os.path.expanduser("~/.agentframework/harness/runs")
R589_DEVICE = os.path.join(REPO, "eval/rover/r589/charlevel_bisect_r589.py")

ROUNDS = ["r585", "r586", "r587", "r588"]
WINDOWS = ["w154", "w155", "w156", "w157", "w158", "w159",
           "w160", "w161", "w162", "w163", "w164", "w165"]
TRUTH_ARM = "codex"
CASE_FAMILIES = ("life", "nim", "sub", "wythoff")

# 形态正则：2 个反斜杠后接字母 n。正确契约在 JSON 字符串内只发单反斜杠 + n。
FORM_RE = re.compile(r"\\\\n")
# 对照口径（同时报，便于人读）：单反斜杠 + n 的总出现数（= 正向外加形态的上位集）
ESC_RE = re.compile(r"\\n")

FAMILY_GAP = 0.9722 - 0.3889  # = 0.5833，R589 实测族间落差（阈值来源，写死在预注册里）


def load_device(path):
    spec = importlib.util.spec_from_file_location("r589_bisect_device", path)
    if spec is None or spec.loader is None:
        raise SystemExit("rc=3 器具读取失败: 无法加载 R589 口径件 %s" % path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # 无副作用（无 module-level main）
    return mod


def sha12(path):
    h = hashlib.sha256()
    with io.open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def read_cases(path):
    """cases.txt -> {'cases': {id: bool}, 'why': {id: reason}, 'n': int}"""
    out = {"cases": {}, "why": {}, "n": 0}
    if not os.path.isfile(path):
        return out
    txt = io.open(path, encoding="utf-8", errors="replace").read()
    for line in txt.splitlines():
        line = line.rstrip()
        if not line.startswith("CASE "):
            continue
        body = line[5:]
        parts = body.split(None, 2)
        if len(parts) < 2:
            continue
        cid, verdict = parts[0], parts[1]
        out["cases"][cid] = (verdict.upper() == "PASS")
        if len(parts) == 3:
            out["why"][cid] = parts[2].strip()
        out["n"] += 1
    return out


def family_of(cid):
    return cid.split("#", 1)[0]


def work_file_count(g1):
    wd = os.path.join(g1, "work")
    if not os.path.isdir(wd):
        return 0
    n = 0
    for _, _, files in os.walk(wd):
        n += len(files)
    return n


def scan_run(round_id, win, arm, device):
    g1 = os.path.join(RUNS, round_id, win, arm, "g1")
    row = {
        "round": round_id, "win": win, "arm": arm, "g1": g1,
        "exists": os.path.isdir(g1),
        "reply_chars": None, "span_found": None, "span_balanced": None,
        "span_chars": None, "parse_ok": None, "parse_err": None,
        "form_n": None, "form_present": None, "esc_n": None,
        "cases_n": None, "family_pass": {}, "all_pass": None,
        "work_files": None, "delivery_absent": None,
    }
    rp = os.path.join(g1, "reply.txt")
    if not os.path.isfile(rp):
        row["reply_missing"] = True
        return row
    txt = io.open(rp, encoding="utf-8", errors="replace").read()
    row["reply_chars"] = len(txt)

    ok, start, span = device.contract_span(txt)
    row["span_found"] = bool(ok)
    row["span_balanced"] = bool(ok)
    row["span_start"] = start
    row["span_chars"] = len(span)
    # 读法（与 POS 控制同一路径，froze 于 v2）: 契约块未闭合时，`contract_span` 返回的是
    # `txt[start:]`（R589 口径），本器**照样在该文本上判形态**并另记 `span_balanced=false`。
    # v1 把未闭合支读成空串 ⇒ 同一条跑次在 POS 控制与 scan_run 上给出**互相矛盾**的形态读数
    # （器具自捕 #1）。v1 读数留档 `escape-census-r590-v1spanpath.json`，不翻案。
    if span:
        try:
            json.loads(span)
            row["parse_ok"] = True
        except Exception as exc:  # noqa: BLE001 — 只记录，不吞
            row["parse_ok"] = False
            row["parse_err"] = "%s: %s" % (type(exc).__name__, exc)
        row["form_n"] = len(FORM_RE.findall(span))
        row["esc_n"] = len(ESC_RE.findall(span))
        row["form_present"] = row["form_n"] > 0
    else:
        row["parse_ok"] = False
        row["parse_err"] = "contract_span_not_found"
        row["form_n"] = 0
        row["esc_n"] = 0
        row["form_present"] = False

    c = read_cases(os.path.join(g1, "cases.txt"))
    row["cases_n"] = c["n"]
    for fam in CASE_FAMILIES:
        ids = [k for k in c["cases"] if family_of(k) == fam]
        passed = sum(1 for k in ids if c["cases"][k])
        row["family_pass"][fam] = {"n": len(ids), "pass": passed,
                                   "all_pass": bool(ids) and passed == len(ids)}
    if c["cases"]:
        row["all_pass"] = all(c["cases"].values())
    row["work_files"] = work_file_count(g1)
    row["delivery_absent"] = row["work_files"] == 0
    return row


def delta(rows, key):
    """Δ = P(target|flag) − P(target|¬flag)；任一侧分母为 0 ⇒ None（不可估，禁报 0）。"""
    a = [r for r in rows if r["form_present"]]
    b = [r for r in rows if not r["form_present"]]

    def rate(rs):
        if not rs:
            return None
        return sum(1 for r in rs if r[key]) / float(len(rs))

    ra, rb = rate(a), rate(b)
    if ra is None or rb is None:
        return {"n_form": len(a), "n_noform": len(b), "rate_form": ra,
                "rate_noform": rb, "delta": None,
                "note": "一侧分母为 0 ⇒ 相关不可估（不报 0）"}
    return {"n_form": len(a), "n_noform": len(b), "rate_form": ra,
            "rate_noform": rb, "delta": ra - rb, "note": None}


def controls(device):
    """成对控制：POS（真机正控）/ NEG1（合成负控）/ NEG2（判别力，防恒假）。"""
    out = {}
    pos = os.path.join(RUNS, "r587", "w162", "agentD-r3", "g1", "reply.txt")
    if os.path.isfile(pos):
        t = io.open(pos, encoding="utf-8", errors="replace").read()
        ok, _, span = device.contract_span(t)
        out["POS_r587_w162_agentD-r3"] = {
            "expect": "form_present=true", "got": bool(span) and bool(FORM_RE.search(span)),
            "n": len(FORM_RE.findall(span)) if span else 0}
    else:
        out["POS_r587_w162_agentD-r3"] = {"expect": "form_present=true", "got": None,
                                          "note": "源件缺失 ⇒ 控制不可行使"}

    neg_src = '{"schema_version":"r1.0","plan":[{"id":"s1","args":{"cmd":"printf \'a\\nb\'"}}]}'
    oks, _, spans = device.contract_span(neg_src)
    out["NEG1_synthetic_correct_escape"] = {
        "expect": "form_present=false", "got": bool(FORM_RE.search(spans)),
        "span_balanced": bool(oks), "json_ok": _json_ok(spans)}

    inj = '{"schema_version":"r1.0","plan":[{"id":"s1","args":{"cmd":"printf \'a\\\\nb\'"}}]}'
    oki, _, spani = device.contract_span(inj)
    out["NEG2_synthetic_injected_form"] = {
        "expect": "form_present=true", "got": bool(FORM_RE.search(spani)),
        "span_balanced": bool(oki), "json_ok": _json_ok(spani)}

    teeth = all(
        (c.get("got") is True) for c in (out["POS_r587_w162_agentD-r3"], out["NEG2_synthetic_injected_form"])
    ) and (out["NEG1_synthetic_correct_escape"].get("got") is False)
    out["has_teeth"] = teeth
    return out


def _json_ok(s):
    if not s:
        return False
    try:
        json.loads(s)
        return True
    except Exception:  # noqa: BLE001
        return False


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=RUNS)
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r590/escape-census-r590.json"))
    a = ap.parse_args(argv)

    device = load_device(R589_DEVICE)
    rows = []
    for r in ROUNDS:
        for w in WINDOWS:
            wd = os.path.join(a.runs, r, w)
            if not os.path.isdir(wd):
                continue
            for arm in sorted(os.listdir(wd)):
                if arm == TRUTH_ARM:
                    continue
                rows.append(scan_run(r, w, arm, device))

    prod = [x for x in rows if x.get("exists")]
    n_prod = len(prod)
    form_rows = [x for x in prod if x["form_present"]]

    occurrence = (len(form_rows) / float(n_prod)) if n_prod else None
    # 主相关：wythoff 整族全对
    for x in prod:
        x["_wythoff_all"] = bool(x["family_pass"].get("wythoff", {}).get("all_pass"))
    d_wy = delta(prod, "_wythoff_all")
    d_abs = delta(prod, "delivery_absent")

    decision = None
    if occurrence is None or n_prod == 0:
        decision = "NO_DATA"
    elif occurrence == 0.0:
        decision = "SELF_FALSIFIED:出现率=0 ⇒ 本候选自证无价值 ⇒ 转记「应改查落点非冷点主因」"
    elif d_wy["delta"] is None:
        decision = "UNESTIMABLE:一侧分母为 0 ⇒ 相关不可估（禁报 0）"
    elif d_wy["delta"] >= FAMILY_GAP:
        decision = "SUPPORTED:Δ_allpass %.4f ≥ 阈值 %.4f ⇒ 形态可解释整族塌陷（只读相关，非因果）" % (
            d_wy["delta"], FAMILY_GAP)
    else:
        decision = "NOT_LOAD_BEARING:Δ_allpass %.4f < 阈值 %.4f ⇒ 形态与整族塌陷非承重" % (
            d_wy["delta"], FAMILY_GAP)

    ctr = controls(device)
    teeth_ok = ctr["has_teeth"] and (ctr["NEG1_synthetic_correct_escape"].get("got") is False) \
        and (ctr["NEG2_synthetic_injected_form"].get("got") is True)
    neg3 = any(x["form_present"] is False for x in prod)

    # ---- post-hoc（明示事后性；预注册判决不因此改写）----
    reasons = {}
    for x in prod:
        for fam in CASE_FAMILIES:
            reasons.setdefault(fam, {})
    for r in ROUNDS:
        for w in WINDOWS:
            wd = os.path.join(a.runs, r, w)
            if not os.path.isdir(wd):
                continue
            for arm in sorted(os.listdir(wd)):
                if arm == TRUTH_ARM:
                    continue
                g1 = os.path.join(wd, arm, "g1")
                c = read_cases(os.path.join(g1, "cases.txt"))
                for cid, why in c["why"].items():
                    fam = family_of(cid)
                    key = re.sub(r"\s+", " ", why.strip())[:60] or "(no-reason)"
                    reasons.setdefault(fam, {})
                    reasons[fam][key] = reasons[fam].get(key, 0) + 1

    n_all = len(prod)
    n_form = len(form_rows)
    posthoc = {
        "post_hoc": True,
        "note": "以下为读数后增补（明示事后性），**不改写**预注册判决；仅用于给「转记落点主因」提供证据面。",
        "form_prevalence_across_all_runs": (n_form / float(n_all)) if n_all else None,
        "form_prevalence_among_wythoff_allpass": d_wy["rate_form"],
        "discrimination_check": {
            "question": "该形态能否区分「wythoff 整族全对」与「未全对」？",
            "rate_form_allpass": d_wy["rate_form"],
            "rate_form_all": (n_form / float(n_all)) if n_all else None,
            "verdict": ("NON_SEPARATING: 形态在整族全对跑次上的出现率≈全体出现率 ⇒ 无判别力"
                        if d_wy["rate_form"] is not None and n_all and
                        abs((d_wy["rate_form"] or 0) - n_form / float(n_all)) < 0.10
                        else "SEPARATING: 出现率有可分差"),
        },
        "failure_reason_census_by_family": reasons,
    }

    payload = {
        "round": "R590",
        "criterion": "C1",
        "mode": "read_only census (零写入 runs/ · 零产品源码改动 · 零远端)",
        "instrument": "eval/rover/r590/escape_form_census_r590.py",
        "instrument_sha12": sha12(os.path.abspath(__file__)),
        "device_read_contract": {
            "contract_span": "import eval/rover/r589/charlevel_bisect_r589.py::contract_span（同口径，禁重写第二份）",
            "device_sha12": sha12(R589_DEVICE),
            "cases_txt": "<runs>/<round>/<win>/<arm>/g1/cases.txt",
            "work_files": "os.walk(<g1>/work) 文件数",
        },
        "form_definition": "契约块内出现「双反斜杠 + 字母 n」（正则 \\\\\\\\n）",
        "scope": {"rounds": ROUNDS, "windows": WINDOWS, "product_runs": n_prod},
        "occurrence": {
            "n_product_runs": n_prod,
            "n_form_present": len(form_rows),
            "rate": occurrence,
            "named": ["%s/%s/%s" % (x["round"], x["win"], x["arm"]) for x in form_rows],
        },
        "correlation_wythoff_allpass": d_wy,
        "correlation_delivery_absent": d_abs,
        "threshold": {"name": "FAMILY_GAP (R589 实测族间落差 0.9722 − 0.3889)", "value": FAMILY_GAP},
        "decision": decision,
        "parse_status": {
            "parse_ok": sum(1 for x in prod if x["parse_ok"]),
            "parse_fail": sum(1 for x in prod if x["parse_ok"] is False),
            "span_not_found": sum(1 for x in prod if not x["span_found"]),
            "fail_named": ["%s/%s/%s :: %s" % (x["round"], x["win"], x["arm"], x["parse_err"])
                           for x in prod if x["parse_ok"] is False][:20],
        },
        "posthoc": posthoc,
        "delivery": {
            "n_absent": sum(1 for x in prod if x["delivery_absent"]),
            "named": ["%s/%s/%s" % (x["round"], x["win"], x["arm"])
                      for x in prod if x["delivery_absent"]],
        },
        "controls": ctr,
        "checks": {
            "C1a_has_teeth": teeth_ok,
            "C1b_neg3_nonconstant_false_exists": neg3,
            "C1c_occurrence_estimable": occurrence is not None,
        },
        "rows": prod,
        "rc": 0,
    }
    if not (teeth_ok and neg3):
        payload["rc"] = 2
        payload["rc_reason"] = "器具无牙（成对控制未全翻面）或形态判据恒真 ⇒ 判据不可用"

    with io.open(a.out, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, indent=1))
    print("OUT=%s rc=%s" % (a.out, payload["rc"]))
    print("occurrence=%s (%d/%d)" % (occurrence, len(form_rows), n_prod))
    print("delta_wythoff=%s" % (d_wy["delta"],))
    print("decision=%s" % decision)
    return payload["rc"]


if __name__ == "__main__":
    sys.exit(main())
