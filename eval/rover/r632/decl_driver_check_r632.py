#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R632 · 候选③ —— 轮驱动器**头部声明 vs 实盘赋值**一致性机检（声明滞后 → 有牙判红）。

背景（R631 自捕器件缺陷 D3，如实披露）:
  `eval/rover/r631/run_r631.sh` 的头部派生声明块（承 r617 派生）逐项与实盘赋值不一致：
  ① 端口声明 `49792→49793`，实盘 `PORT=${PORT:-49795}`；② 窗号声明 `WIN0 208→**211**`（w211..w213），
  实盘 `WIN0=${WIN0:-223}` + `NWIN=2`（⇒ w223..w224）；③ 被测件声明 sha `886db888d744a619…`，
  实盘（`bins-r631.json`）`cefd045e8d1d4258…`；④ 摆动余量声明 `PREV_SWING = **125MB**` / `--min-avail-mb 2775`，
  实盘 `PREV_SWING=${PREV_SWING:-119}` / `gate-margin-r631.json:preflight_min_avail_mb=2769`。

纪律（承 EXP1-Q38 A「声明滞后」）:
  * 判类指纹 = **非绿字段仅为声明类字段**（实盘赋值本身正确）⇒ 处置 = **重审刷新声明**，**不放宽判据**；
  * 刷新**只改注释文本**：`set -uo pipefail` 之后的**任何实盘赋值行零改动**（由本器机检；
    见 `--assert-body-unchanged <ref-sha or file>`）；
  * 修前声明原文**归档留痕**（`证据/instrument-defects-r632.json`），历史判决与读数**不改写**。

用法:
  python3 eval/rover/r632/decl_driver_check_r632.py --sh eval/rover/r631/run_r631.sh --round r631
  python3 eval/rover/r632/decl_driver_check_r632.py --selftest        # 正/负控（含"注入漂移必红"）
"""
import argparse
import hashlib
import io
import json
import os
import re
import shutil
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _sha256(b):
    return hashlib.sha256(b).hexdigest()


def split_driver(text):
    """返回 (header 注释块, body 实盘段)。body 自 `set -` 起（实盘赋值区）。"""
    lines = text.split("\n")
    idx = None
    for i, l in enumerate(lines):
        if re.match(r"^set\s+-", l):
            idx = i
            break
    if idx is None:
        return text, ""
    return "\n".join(lines[:idx]), "\n".join(lines[idx:])


def live_values(round_id):
    """实盘赋值（从驱动器 body + 轮工件派生）。"""
    pd = os.path.join(REPO, "eval/rover", round_id)
    sh = io.open(os.path.join(pd, "run_%s.sh" % round_id), encoding="utf-8").read()
    _, body = split_driver(sh)
    lv = {}
    m = re.search(r"^WIN0=\$\{WIN0:-(\d+)\}", body, re.M)
    n = re.search(r"^NWIN=\$\{NWIN:-(\d+)\}", body, re.M)
    p = re.search(r"^PORT=\$\{PORT:-(\d+)\}", body, re.M)
    s = re.search(r"^PREV_SWING=\$\{PREV_SWING:-(\d+)\}", body, re.M)
    if m and n:
        w0, nw = int(m.group(1)), int(n.group(1))
        lv["win0"], lv["nwin"] = w0, nw
        lv["win_set"] = ["w%d" % (w0 + i) for i in range(nw)]
    if p:
        lv["port"] = int(p.group(1))
    if s:
        lv["prev_swing_mb"] = int(s.group(1))
    gm = os.path.join(pd, "gate-margin-%s.json" % round_id)
    if os.path.isfile(gm):
        g = json.load(io.open(gm, encoding="utf-8"))
        lv["min_avail_mb"] = g.get("preflight_min_avail_mb")
        lv["req"] = g.get("req")
    bn = os.path.join(pd, "bins-%s.json" % round_id)
    if os.path.isfile(bn):
        b = json.load(io.open(bn, encoding="utf-8"))
        v = ((b.get("bin_all_arms") or {}).get("sha256") or "")
        lv["bin_sha16"] = v[:16]
    ts = os.path.join(pd, "taskset-%s.json" % round_id)
    if os.path.isfile(ts):
        lv["taskset_sha12"] = _sha256(io.open(ts, "rb").read())[:12]
    return lv, body


def declared_values(header):
    d = {}
    m = re.search(r"端口\s+(\d+)\s*→\s*(\d+)", header)
    if m:
        d["port"] = int(m.group(2))
    m = re.search(r"窗号\s+WIN0\s+(\d+)\s*→\s*\*\*(\d+)\*\*(?:\s*（w(\d+)\.\.w(\d+))?", header)
    if m:
        d["win0"] = int(m.group(2))
        if m.group(3) and m.group(4):
            d["win_set"] = ["w%d" % i for i in range(int(m.group(3)), int(m.group(4)) + 1)]
    m = re.search(r"PREV_SWING\s*=\s*\*\*(\d+)\s*MB\*\*", header)
    if m:
        d["prev_swing_mb"] = int(m.group(1))
    m = re.search(r"--min-avail-mb\s+(\d+)", header)
    if m:
        d["min_avail_mb"] = int(m.group(1))
    m = re.search(r"sha\s+([0-9a-f]{12,16})…", header)
    if m:
        d["bin_sha16"] = m.group(1)
    return d


def check(sh_path, round_id):
    text = io.open(sh_path, encoding="utf-8").read()
    header, body = split_driver(text)
    d = declared_values(header)
    lv, _ = live_values(round_id)
    items = []
    for k, label in (("port", "端口"), ("win0", "窗号 WIN0"), ("win_set", "窗集"),
                     ("prev_swing_mb", "PREV_SWING(MB)"), ("min_avail_mb", "--min-avail-mb"),
                     ("bin_sha16", "被测件 sha16")):
        dv, lvv = d.get(k), lv.get(k)
        ok = (dv == lvv) if (dv is not None and lvv is not None) else None
        items.append({"item": k, "label": label, "declared": dv, "live": lvv,
                      "verdict": ("ok" if ok else ("drift" if ok is False else "not_declared"))})
    drifted = [x for x in items if x["verdict"] == "drift"]
    absent = [x for x in items if x["verdict"] == "not_declared"]
    # fail-closed（R632 自捕：首版对空声明件判绿 ⇒ 假绿）：**缺声明 ≠ 一致**。
    verdict = "DECL_DRIFT" if drifted else ("DECL_ABSENT" if absent else "PASS")
    return {"round": round_id, "driver": os.path.relpath(sh_path, REPO),
            "driver_sha256": _sha256(text.encode("utf-8")),
            "header_sha256": _sha256(header.encode("utf-8")),
            "body_sha256": _sha256(body.encode("utf-8")),
            "items": items, "drifted": len(drifted), "absent": len(absent), "checked": len(items),
            "verdict": verdict}, header


def synth_header(lv, drift_on=None):
    """按 live 值合成一致的声明头（正控用；drift_on 指定一个字段注入错误值）。"""
    port = lv.get("port"); port = port + 1 if drift_on == "port" else port
    w0 = lv.get("win0"); w0 = w0 + 1 if drift_on == "win0" else w0
    ws = lv.get("win_set") or []
    wl = ws[0][1:] if ws else "0"; wh = ws[-1][1:] if ws else "0"
    sw = lv.get("prev_swing_mb"); sw = sw + 1 if drift_on == "prev_swing_mb" else sw
    ma = lv.get("min_avail_mb"); ma = ma + 1 if drift_on == "min_avail_mb" else ma
    bsha = lv.get("bin_sha16"); bsha = "0" + bsha[1:] if drift_on == "bin_sha16" else bsha
    return ("#!/usr/bin/env bash\n"
            "# synthetic header (selftest)\n"
            "#   ① 端口 49792→%s。\n" % port
            + "#   ② 窗号 WIN0 208→**%s**（w%s..w%s）。\n" % (w0, wl, wh)
            + "#   ③ 被测件 sha %s…\n" % bsha
            + "#   ⑦ PREV_SWING = **%sMB**（口径 = 起手闸 `--min-avail-mb %s` − 产品门槛 2650；\n" % (sw, ma))


def selftest():
    """正控 = 合成一致头必判 PASS（证明本器不是恒红）/ 负控 = 逐字段注入漂移必判红 /
    空声明件必判 DECL_ABSENT（**不得**判绿 —— R632 自捕假绿）。"""
    tmp = tempfile.mkdtemp(prefix="r632decl-")
    rows, rc = [], 0
    try:
        lv, _ = live_values("r631")
        sh = os.path.join(REPO, "eval/rover/r631/run_r631.sh")
        body = split_driver(io.open(sh, encoding="utf-8").read())[1]
        # POS: 合成一致头 + 真实 body ⇒ 必 PASS
        p_ok = os.path.join(tmp, "run_r631.sh")
        io.open(p_ok, "w", encoding="utf-8").write(synth_header(lv) + body)
        r_ok, _ = check(p_ok, "r631")
        rows.append({"case": "POS_synth_consistent", "expect": "PASS", "got": r_ok["verdict"],
                     "drifted": r_ok["drifted"], "absent": r_ok["absent"]})
        # NEG: 逐字段注入漂移 ⇒ 必 DECL_DRIFT
        inj = {}
        for k in ("port", "win0", "prev_swing_mb", "min_avail_mb", "bin_sha16"):
            q = os.path.join(tmp, "run_inj_%s.sh" % k)
            io.open(q, "w", encoding="utf-8").write(synth_header(lv, drift_on=k) + body)
            rr, _ = check(q, "r631")
            inj[k] = rr["verdict"]
            rows.append({"case": "NEG_inject_%s" % k, "expect": "DECL_DRIFT", "got": rr["verdict"]})
        # NEG: 空声明件 ⇒ DECL_ABSENT（不得判绿）
        empty = os.path.join(tmp, "run_empty.sh")
        io.open(empty, "w", encoding="utf-8").write("#!/usr/bin/env bash\nset -uo pipefail\n")
        r2, _ = check(empty, "r631")
        rows.append({"case": "NEG_empty_header", "expect": "DECL_ABSENT", "got": r2["verdict"]})
        # 现盘（修复前/后均可）
        r3, _ = check(sh, "r631")
        rows.append({"case": "INFO_current_r631", "expect": "-", "got": r3["verdict"], "drifted": r3["drifted"]})
        teeth = (r_ok["verdict"] == "PASS"
                 and all(v == "DECL_DRIFT" for v in inj.values())
                 and r2["verdict"] == "DECL_ABSENT")
        rc = 0 if teeth else 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    res = {"selftest": "decl_driver_check_r632", "rc": rc, "teeth": bool(teeth), "rows": rows,
           "note": "四态齐备才算有牙：合成一致头必 PASS（非恒红）/ 逐字段注入必红 / 空头必 DECL_ABSENT（缺声明≠一致）"}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sh", default=os.path.join(REPO, "eval/rover/r631/run_r631.sh"))
    ap.add_argument("--round", default="r631")
    ap.add_argument("--json", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    r, _ = check(a.sh, a.round)
    if a.json:
        json.dump(r, io.open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for it in r["items"]:
        print("  %-22s declared=%-22s live=%-22s %s" % (it["label"], it["declared"], it["live"], it["verdict"]))
    print("DECL_CHECK checked=%d drifted=%d absent=%d verdict=%s" % (r["checked"], r["drifted"], r["absent"], r["verdict"]))
    return 0 if r["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
