#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R599 候选③ 器具: **真值侧（codex）wythoff 两例的文本级定因**（只读 + 副本内复现）。

背景（R598 候选② 只读普查的读数）: 真值臂对 `wythoff#43-public` 与 `wythoff#57-hidden` 在第 4 窗起**逐字重复**
失败（w173 / w175 / w176 / w178）⇒ 判「真值臂自身可复现弱点」。R599 候选③ = 把该「弱点」**落到文本层**：
真值臂产出 vs 期望逐字比对，判它是①格式差异 ②语义差异 ③未能复现（判分口径差）。

纪律:
  · **只在副本上复跑**（`tempfile.mkdtemp` + `shutil.copytree`），冻结夹具与快照一字不改；`PYTHONDONTWRITEBYTECODE=1`。
  · 用例名与判分口径**由产物侧脚本自身派生**（`%s#%02d-%s`，与 `cases/run_cases_r521.py` 同源），不手打。
  · 三态判决 + 成对控制: NC-D（确定性: 同例两次逐字节相同）/ NC-T（非平凡: 跨两例读数互异或非空）/ POS（把期望换成产出 ⇒ 分类必须翻成 match）。
  · rc 分层: 0 可用 / 2 器具缺陷（控制未过）/ 3 输入缺失（fail-closed）。

用法: python3 eval/rover/r599/truthgap2_r599.py [--rounds r596,r597,r598,r599]
      [--out eval/rover/r599/truthgap-r599.json]
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = "/home/agentuser/AgentFramework"
CASES = os.path.join(REPO, "eval/rover/r599/cases/cases-r521.json")
RUNS = os.path.expanduser("~/.agentframework/harness/runs")
TMO = 10.0
CASE_RE = re.compile(r"^CASE (\S+) (PASS|FAIL) (\S*)$", re.M)
TARGETS = (43, 57)          # 索引面（与用例脚本的 %02d 同名）


def sha12(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8", "replace")).hexdigest()[:12]


def load_cases():
    with io.open(CASES, encoding="utf-8") as fh:
        return json.load(fh)


def case_name(cases, i: int) -> str:
    c = cases[i]
    return "%s#%02d-%s" % (c["game"], i, c["vis"])


def read_cases_txt(p: str):
    if not os.path.exists(p):
        return None
    t = io.open(p, encoding="utf-8", errors="replace").read()
    return {m.group(1): (m.group(2) == "PASS", m.group(3)) for m in CASE_RE.finditer(t)}


def normalize(s: str) -> str:
    return "\n".join(ln.rstrip() for ln in s.strip("\n").split("\n")).strip()


def first_diff(a: str, b: str):
    la, lb = a.split("\n"), b.split("\n")
    for i in range(max(len(la), len(lb))):
        x = la[i] if i < len(la) else "<缺行>"
        y = lb[i] if i < len(lb) else "<缺行>"
        if x != y:
            return {"line": i, "actual": x[:120], "expected": y[:120]}
    return None


def reproduce(snapshot_g1: str, cases, idx: int):
    """在**副本**上复跑单例，返回 (rc, stdout, stderr_tail)。"""
    c = cases[idx]
    tmp = tempfile.mkdtemp(prefix="tg599-")
    try:
        shutil.copytree(snapshot_g1, tmp, dirs_exist_ok=True)
        env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": tmp,
               "PYTHONPATH": tmp, "PYTHONDONTWRITEBYTECODE": "1"}
        p = subprocess.run([sys.executable, "-B", "-m", "games", c["game"]], input=c["stdin"],
                           capture_output=True, text=True, timeout=TMO, cwd=tmp, env=env)
        return p.returncode, p.stdout, (p.stderr or "")[-200:]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def solver_excerpt(snapshot_g1: str, game: str, limit: int = 320) -> str:
    """取该游戏实现文件的片段作证据（只读副本，禁在被测树上跑）。"""
    best = ""
    for root, _dirs, fns in os.walk(snapshot_g1):
        for fn in sorted(fns):
            if not fn.endswith(".py"):
                continue
            fp = os.path.join(root, fn)
            try:
                t = io.open(fp, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            if game in t and ("def " in t):
                best = "%s :: %s" % (os.path.relpath(fp, snapshot_g1), t[:limit])
                break
        if best:
            break
    return best


def classify(rc: int, actual: str, expected: str):
    exp_n = expected.strip("\n")
    if rc != 0:
        return "semantic", {"reason": "rc=%d(非零退出)" % rc, "diff": first_diff(actual, expected)}
    act_n = actual.strip("\n")
    if act_n == exp_n:
        return "match", {"note": "副本内复跑与期望一致 ⇒ 判分口径差（未复现）"}
    if normalize(actual) == normalize(expected):
        return "format", {"note": "仅尾空白/空行差异", "diff": first_diff(actual, expected)}
    return "semantic", {"diff": first_diff(actual, expected)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", default="r596,r597,r598,r599")
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r599/truthgap-r599.json"))
    a = ap.parse_args()
    if not os.path.exists(CASES):
        print("[fail-closed] 缺冻结用例 %s" % CASES)
        return 3
    cases = load_cases()
    names = {case_name(cases, i): i for i in TARGETS}
    for i in TARGETS:
        if cases[i]["game"] != "wythoff":
            print("[fail-closed] 索引 %d 非 wythoff（用例序变了 ⇒ 拒绝按旧索引定因）" % i)
            return 3
    rows, missing = [], []
    for r in a.rounds.split(","):
        r = r.strip()
        snap_root = os.path.join(REPO, "eval/rover", r, "snapshots")
        if not os.path.isdir(snap_root):
            missing.append(snap_root)
            continue
        for win in sorted(os.listdir(snap_root)):
            for side in ("codex", "agentD-r1", "agentD-r2", "agentD-r3"):
                g1 = os.path.join(snap_root, win, side, "g1")
                if not os.path.isdir(g1):
                    continue
                ctxt = read_cases_txt(os.path.join(RUNS, r, win, side, "g1", "cases.txt"))
                for name, idx in names.items():
                    got = (ctxt or {}).get(name)
                    row = {"round": r, "win": win, "side": side, "case": name,
                           "judge": (None if got is None else ("PASS" if got[0] else "FAIL")),
                           "why": (None if got is None else got[1]), "reproduced": None}
                    if got is not None and not got[0]:      # 只对**真值/产品判 FAIL 的例**做文本级定因
                        rc, out, err = reproduce(g1, cases, idx)
                        cls, det = classify(rc, out, cases[idx]["expected_stdout"])
                        rc2, out2, _ = reproduce(g1, cases, idx)
                        row.update({"reproduced": True, "rc": rc, "class": cls, "detail": det,
                                    "produced_stdout": out[:600], "expected_stdout": cases[idx]["expected_stdout"][:600],
                                    "stdout_sha12": sha12(out), "stderr_tail": err,
                                    "deterministic": (out == out2 and rc == rc2),
                                    "solver_excerpt": solver_excerpt(g1, cases[idx]["game"])})
                        # POS 注入: 期望 := 产出 ⇒ 分类必须翻成 match（判据可翻面，非恒真）
                        cls_pos, _ = classify(rc, out, out)
                        row["pos_flip_to_match"] = (cls_pos == "match")
                    rows.append(row)
    # ---- 成对控制 ----
    det_rows = [r for r in rows if r.get("reproduced")]
    nc_d = bool(det_rows) and all(r["deterministic"] for r in det_rows)
    nc_t = len({(r["case"], r["class"]) for r in det_rows}) >= 2 and any(r["produced_stdout"].strip() for r in det_rows)
    pos_ok = bool(det_rows) and all(r["pos_flip_to_match"] for r in det_rows)
    codex_rows = [r for r in det_rows if r["side"] == "codex"]
    prod_rows = [r for r in det_rows if r["side"] != "codex"]
    out = {
        "round": "R599", "purpose": "候选③ 真值侧（codex）wythoff 两例文本级定因（只读 + 副本内复现）",
        "instrument": {"path": os.path.abspath(__file__), "sha12": sha12(io.open(__file__, encoding="utf-8").read()),
                       "cases_sha12": sha12(io.open(CASES, encoding="utf-8").read()),
                       "case_names": sorted(names.keys()),
                       "case_contract": "用例名 = %s#%02d-%s（与 cases/run_cases_r521.py 同源派生，禁手打）"
                                        % ("<game>", 0, "<vis>")},
        "scope": {"rounds": a.rounds.split(","), "missing_roots": missing,
                  "instances_with_repro": len(det_rows), "codex": len(codex_rows), "product": len(prod_rows)},
        "controls": {"NC-D_determinism": nc_d, "NC-T_nontrivial": nc_t, "POS_flip": pos_ok},
        "codex_class_hist": {k: sum(1 for r in codex_rows if r["class"] == k) for k in ("match", "format", "semantic")},
        "rows": rows,
        "rc": 0 if (nc_d and nc_t and pos_ok) else 2,
    }
    with io.open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("[truthgap2] 复现实例=%d (codex=%d/产品=%d) 控制 NC-D=%s NC-T=%s POS=%s ⇒ rc=%d"
          % (len(det_rows), len(codex_rows), len(prod_rows), nc_d, nc_t, pos_ok, out["rc"]))
    for r in codex_rows:
        print("  · %s/%s codex %s -> %s | %s" % (r["round"], r["win"], r["case"], r["class"],
                                                 json.dumps(r["detail"], ensure_ascii=False)[:160]))
    return 0 if out["rc"] == 0 else out["rc"]


if __name__ == "__main__":
    raise SystemExit(main())
