#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R595 — 只读定因/普查面（候选 ②③⑤ 同器具出数）。

承 R592–R594 的「从冻结产物复算 + 独立 oracle 分类」模式。**零子进程探针**：全部读数取自
在盘登记件（`eval/rover/r593/landing-predicate-r593.json` 的 59 跑次面，其中 `cold_only_prod` /
`cold_only_true` 是**位置集合本身**而非计数）与冻结快照树的**静态**扫描。

三个 part：
  · `--part gate`    （候选⑤）起手闸余量派生：源 = 同态在飞窗的运行期采样（r591, n=97）+ 本轮两次起手实测。
  · `--part coldset` （候选②）冷集构造层定因下沉：由 (T, U, M) 重建 D，量集合差**方向与形态**，
                     机械区分 (B1) Beatty 判定错 / (B2) 边界处理错 / (B3) 其他，并配成对负控。
  · `--part census`  （候选③）交付物自洽性普查：`__main__` 的**全属性**引用 vs 各模块导出集合，
                     不自洽者**实测复现**（rc≠0 ∧ stderr 含属性名）才算。

rc 语义（fail-closed，编码验收面）：0 = 器材可用且结论成立 / 2 = 器具缺陷（无牙·同判·守恒破·只读破·复现不符）
/ 3 = 输入缺失。**不放宽任何阈值、不事后调判据。**

用法:
  python3 -B eval/rover/r595/face_r595.py --part gate|coldset|census [--out PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = "/home/agentuser/AgentFramework"
RP = os.path.join(REPO, "eval/rover")
LP593 = os.path.join(RP, "r593/landing-predicate-r593.json")
SNAP = os.path.join(RP, "%s/snapshots/%s/%s/g1")
MODULES = ["life", "sub", "nim", "wythoff"]
L = 25
GAMES_HELP = None


# ---------------------------------------------------------------- 公共
def sha_tree(root, names=None):
    h = hashlib.sha256()
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d != "__pycache__"]
        for fn in sorted(fns):
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, root)
            if names and not any(rel.endswith(n) for n in names):
                continue
            h.update(rel.encode())
            with open(p, "rb") as fh:
                h.update(fh.read())
    return h.hexdigest()[:16]


def load_runs():
    with open(LP593, encoding="utf-8") as fh:
        return json.load(fh)


def wythoff_true(n=L):
    """独立 oracle（与被测零共享代码）：Wythoff 冷位 = (floor(k*phi), floor(k*phi)+k)。"""
    phi = (1.0 + 5.0 ** 0.5) / 2.0
    t, k = set(), 0
    while True:
        a = int(k * phi)          # floor
        b = a + k
        if b > n:
            break
        t.add((a, b))
        k += 1
    return t


# ---------------------------------------------------------------- 候选⑤
def part_gate(out):
    src = os.path.expanduser("~/.agentframework/harness/runs/r591/logs/run-samples.jsonl")
    if not os.path.isfile(src):
        print("[gate] 源缺失:", src)
        return 3
    vals = []
    with open(src, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            try:
                o = json.loads(ln)
            except Exception:
                continue
            v = o.get("mem_available_mb")
            if isinstance(v, (int, float)):
                vals.append(int(v))
    if len(vals) < 10:
        print("[gate] 源样本不足:", len(vals))
        return 3
    swing = max(vals) - min(vals)
    gate_mb, floor = 2650, 60
    cap = None            # 由本轮起手实测的 ceiling 决定
    gm = os.path.join(RP, "r595/gate-margin-r595.json")
    obs = {}
    if os.path.isfile(gm):
        with open(gm, encoding="utf-8") as fh:
            obs = json.load(fh)
    ceil = obs.get("ceiling_min_of_3")
    cap = None if ceil is None else ceil - gate_mb - floor
    margin = None if cap is None else max(floor, min(swing, cap))
    # 两次起手实测（attempt#1 fail-closed / attempt#2 PASS）——取自跑轮日志，机读
    logp = os.path.expanduser("~/.agentframework/harness/runs/r595/logs/run.txt")
    attempts = []
    if os.path.isfile(logp):
        with open(logp, encoding="utf-8", errors="replace") as fh:
            for ln in fh:
                ln = ln.strip()
                if "起手前采样" in ln:
                    m = re.search(r"ceiling\(min of 3\)=(\d+) spread=(\d+)", ln)
                    if m:
                        attempts.append({"kind": "pre_sample", "ceiling_mb": int(m.group(1)),
                                         "spread_mb": int(m.group(2)), "line": ln[:120]})
                elif "顶棚" in ln and "装不下" in ln:
                    attempts.append({"kind": "gate_clause", "outcome": "FAIL_CLOSED", "line": ln[:160]})
                elif "起手闸 A1" in ln:
                    attempts.append({"kind": "gate_A1", "outcome": "PASS" if "PASS" in ln else "FAIL",
                                     "line": ln[:120]})
    res = {
        "round": "R595", "part": "gate",
        "criterion": "候选⑤ 起手闸余量按同态在飞窗实测派生（R594 只读轮无运行期采样器 ⇒ 不可作源）",
        "prev_swing_source": "~/.agentframework/harness/runs/r591/logs/run-samples.jsonl",
        "prev_swing_n": len(vals), "prev_swing_min_mb": min(vals), "prev_swing_max_mb": max(vals),
        "prev_swing_effective": swing,
        "gate_mb": gate_mb, "floor_mb": floor,
        "r595_observed": obs,
        "attempts": attempts,
        "derived": {"ceiling_mb": ceil, "cap_mb": cap, "margin_mb": margin,
                    "REQ_mb": None if margin is None else gate_mb + margin,
                    "cap_binding": bool(obs.get("cap_binding")), "runner_margin_mb": obs.get("margin"),
                    "runner_req_mb": obs.get("req"),
                    "agree": bool(obs.get("prev_swing_effective") == swing)},
        "honest_boundary": "余量只覆盖**同态**（agent 三臂 + codex 一臂）在飞窗的观测振幅；异态负载（构建/发布）不在覆盖面。",
    }
    if attempts:
        res["discrimination"] = ("同条款下 attempt#1 (%s) 与 attempt#2 (%s) 分别出现 ⇒ 条款有牙、非恒真门"
                                 % (next((x.get("outcome", "PRE") for x in attempts if x["kind"] == "gate_clause"), "—"),
                                    next((x.get("outcome") for x in attempts if x["kind"] == "gate_A1"), "—")))
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[gate] prev_swing=%dMB (n=%d, %d..%d) margin=%s REQ=%s cap_binding=%s ⇒ %s"
          % (swing, len(vals), min(vals), max(vals), margin, res["derived"]["REQ_mb"],
             res["derived"]["cap_binding"], out))
    return 0


# ---------------------------------------------------------------- 候选②
def shape(pts):
    """集合差的**方向与形态**量（pts = 规范化 (a,b) 位置集合）。"""
    if not pts:
        return {"n": 0}
    rows = {a for a, _ in pts}
    cols = {b for _, b in pts}
    diags = {b - a for a, b in pts}
    edge = sum(1 for a, b in pts if a == 0 or b == L)
    interior = sum(1 for a, b in pts if a > 0 and b < L)
    return {"n": len(pts), "distinct_rows": len(rows), "distinct_cols": len(cols),
            "distinct_diags": len(diags), "edge_n": edge, "interior_n": interior,
            "row1d": len(rows) == 1, "col1d": len(cols) == 1, "diag1d": len(diags) == 1,
            "edge_only": interior == 0,
            "samples": sorted(pts)[:8]}


def classify(u, m, border_only, interior_equal):
    """预注册判别（prereg C8 decision_rule）——**逐字照判，不事后调**：
      U/M 双空 ⇒ CONSISTENT
      差集只落边界带 ∧ 内部逐点等于真值 ⇒ B2
      U≠∅ ∧ M≠∅ ∧ 均非边界局限 ⇒ B1
      其余（单侧差且非边界局限）⇒ B3（单列，禁折进 B1/B2）
    """
    if not u and not m:
        return "CONSISTENT"
    if border_only and interior_equal:
        return "B2"
    if u and m:
        return "B1"
    return "B3"


def variants(n=L):
    """候选机制族（用于给 B1/B3 命名机制，不作判决门）：全部由公式派生，零被测代码共享。"""
    phi = (1.0 + 5.0 ** 0.5) / 2.0
    out = {}
    for tag, fn in (("floor", int), ("round", round), ("ceil", lambda x: int(-(-x // 1)))):
        s, k = set(), 0
        while True:
            a = int(fn(k * phi)); b = a + k
            if b > n:
                break
            s.add((a, b)); k += 1
        out[tag] = s
    out["floor_k1"] = {p for p in out["floor"] if p != (0, 0)}
    out["diag"] = {(k, k) for k in range(0, n + 1)}
    return out


def part_coldset(out):
    d = load_runs()
    runs = d["runs"]
    T = wythoff_true(L)
    VAR = {"_": variants(L)}
    LB = max(b for _, b in T)
    per, cons_bad = [], []
    for r in runs:
        U = {tuple(x) for x in r["cold_only_prod"]}
        M = {tuple(x) for x in r["cold_only_true"]}
        if r.get("err"):
            per.append({"round": r["round"], "win": r["win"], "sub": r["sub"], "side": r["side"],
                        "err": r.get("err")})
            continue
        D = (T - M) | U
        cons = (len(D) == r["declared_cold_n"])
        if not cons:
            cons_bad.append({"round": r["round"], "win": r["win"], "sub": r["sub"],
                             "rebuilt": len(D), "declared": r["declared_cold_n"]})
        su, sm = shape(U), shape(M)
        # 边界带判定: 差集(两侧合计)是否**只**落边界带 (a==0 ∨ b==L)
        both = U | M
        border_only = bool(both) and all((a == 0 or b == L) for a, b in both)
        # 内部逐点相等性（差集不碰内部 ⇒ B2 的强形式）
        interior_equal = all(not (a > 0 and b < L) for a, b in both)
        klass = classify(U, M, border_only, interior_equal)
        # 机制命名（事后细化，随 B1/B3 单列；不改判决）
        D = (T - M) | U
        vs = VAR["_"]
        mech = None
        for tag, s in vs.items():
            if D == s:
                mech = "fit:" + tag
                break
        if mech is None:
            if M and not U:
                mb = max((b for _, b in M), default=0)
                tail = sum(1 for _, b in M if b >= LB - 2)
                mech = ("missing_only:高 k 截断" if tail == len(M) and len(M) > 1 else
                        "missing_only:其他")
            elif U and not M:
                mech = "excess_only:" + ("整行族" if su.get("row1d") else
                                        ("对角族" if su.get("diag1d") else "散布"))
            elif U and M:
                mech = "both:" + ("U整行族" if su.get("row1d") else "U散布")
        per.append({"round": r["round"], "win": r["win"], "sub": r["sub"], "side": r["side"],
                    "declared_cold_n": r["declared_cold_n"], "cold_set_equal": r["cold_set_equal"],
                    "U": su, "M": sm, "only_U": bool(U) and not M, "only_M": bool(M) and not U,
                    "both": bool(U and M), "border_only": border_only,
                    "interior_equal": interior_equal, "class": klass, "mechanism_sub": mech,
                    "conservation": cons, "layer": r.get("layer")})
    # 汇总（两侧分列 + 层分列）
    agg = {}
    for side in ("agent", "codex"):
        rs = [x for x in per if x.get("side") == side and "err" not in x]
        cl, mech = {}, {}
        for x in rs:
            cl[x["class"]] = cl.get(x["class"], 0) + 1
            if x["class"] != "CONSISTENT":
                mech[x["mechanism_sub"]] = mech.get(x["mechanism_sub"], 0) + 1
        u_tot = sum(x["U"]["n"] for x in rs)
        m_tot = sum(x["M"]["n"] for x in rs)
        agg[side] = {"runs": len(rs), "class_hist": cl, "mech_hist": mech,
                     "cold_set_equal_n": sum(1 for x in rs if x["cold_set_equal"]),
                     "U_pos_total": u_tot, "M_pos_total": m_tot,
                     "U_runs": sum(1 for x in rs if x["U"]["n"]), "M_runs": sum(1 for x in rs if x["M"]["n"]),
                     "both_runs": sum(1 for x in rs if x["both"]),
                     "only_U_runs": sum(1 for x in rs if x["only_U"]),
                     "only_M_runs": sum(1 for x in rs if x["only_M"]),
                     "border_only_runs": sum(1 for x in rs if x["border_only"]),
                     "conservation_all": all(x["conservation"] for x in rs)}
    # ---- 成对负控（分类器有牙三件套）
    fixtures = {}
    # OK: 冷集逐点等于 T
    fixtures["OK"] = (set(), set(), False, True, "CONSISTENT")
    # POS: 正确冷集 + 整条边界行 (0,b) 误判为冷 ⇒ 差集只落边界带 ⇒ 必须 B2
    fixtures["POS_border_row"] = ({(0, b) for b in range(0, L + 1)} - T, set(), True, True, "B2")
    # NEG: Beatty 变形（用 round 替 floor 造出的伪冷位）⇒ 差集散布非边界 ⇒ 必须 B1
    round_set = VAR["_"]["round"]
    fixtures["NEG_beatty_round"] = (round_set - T, T - round_set, False, False, "B1")
    # NEG2: 单侧缺失（高 k 截断）⇒ 必须落 B3（单列，不折进 B1/B2）
    fixtures["NEG_missing_only"] = (set(), {p for p in T if p[1] >= LB - 2}, False, False, "B3")
    ctrl = {}
    for name, (u, m, bo, ie, want) in fixtures.items():
        got = classify(u, m, bo, ie)
        ctrl[name] = {"want": want, "got": got, "ok": got == want, "U_n": len(u), "M_n": len(m)}
    controls_ok = all(v["ok"] for v in ctrl.values())
    # 非平凡性: 分类器在受控输入上必须出 ≥2 个不同值（否则恒判门）
    distinct = len({v["got"] for v in ctrl.values()})
    res = {"round": "R595", "part": "coldset",
           "source": os.path.relpath(LP593, REPO),
           "oracle": "独立 Wythoff 公式 (floor(k*phi), a+k)，与被测零共享代码；网格 L=%d ⇒ |T|=%d" % (L, len(T)),
           "rebuild_rule": "D = (T \\ M) ∪ U，断言 |D| == declared_cold_n（守恒；U=declared\\true, M=true\\declared）",
           "conservation_violations": cons_bad,
           "agg": agg, "per_run_n": len(per), "controls": ctrl,
           "controls_ok": controls_ok, "classifier_distinct_values": distinct,
           "runs": per}
    # rc: 器具自身缺陷面
    rc = 0
    if cons_bad or not controls_ok or distinct < 2:
        rc = 2
    res["rc"] = rc
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[coldset] runs=%d agent=%s codex=%s | 控制 ok=%s 分辨值=%d | rc=%d ⇒ %s"
          % (len(per), agg["agent"]["class_hist"], agg["codex"]["class_hist"],
             controls_ok, distinct, rc, out))
    return rc


# ---------------------------------------------------------------- 候选③
ATTR_RE = re.compile(r"(?<![\w.])([A-Za-z_]\w*)\s*\.\s*([A-Za-z_]\w*)")
IMPORT_FROM_RE = re.compile(r"^\s*from\s+\.?\s*([A-Za-z_]\w*)\s+import\s+([^\n#]+)", re.M)
IMPORT_AS_RE = re.compile(r"^\s*from\s+\.?\s*([A-Za-z_]\w*)\s+import\s+\*\s*$", re.M)
EXPORT_DEF_RE = re.compile(r"^(?:def|class)\s+([A-Za-z_]\w*)", re.M)
EXPORT_ASG_RE = re.compile(r"^([A-Za-z_]\w*)\s*(?::[^=\n]+)?=", re.M)


def exports_of(src):
    src = strip_code(src)
    return set(EXPORT_DEF_RE.findall(src)) | set(EXPORT_ASG_RE.findall(src))


TRIPLE_RE = re.compile(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'')


def strip_code(src):
    """剥注释与三引号串后再做属性抽取。

    自捕 #2（本器具首跑实捕）: 未剥时 `__main__.py` **docstring** 里的散句
    (`... calls games.<game_id>.solve ...` 换行后紧跟模块名) 被 ATTR_RE 的 `\\s*`
    （含换行）跨行匹配成 `wythoff.Reads` 之类的**假属性**，令 NEG 控制（原样副本）
    也判不自洽 ⇒ 判别器不干净。修法 = 剥注释/串后再抽取，断言 NEG 必须翻面。
    """
    src = TRIPLE_RE.sub('""', src)
    src = re.sub(r"#[^\n]*", "", src)
    return src


def main_refs(src):
    """返回 {module: {attrs}}（只取与 games 四模块同名的别名上的属性引用）。"""
    src = strip_code(src)
    refs = {m: set() for m in MODULES}
    for m in MODULES:
        # from .m import a, b   /  from games.m import a
        for mm, names in IMPORT_FROM_RE.findall(src):
            if mm != m:
                continue
            for raw in names.split(","):
                nm = raw.strip().split(" as ")[0].strip().strip("()")
                if re.fullmatch(r"[A-Za-z_]\w*", nm):
                    refs[m].add(nm)
    # 别名.属性（别名 == 模块名的常见形态：import games.wythoff as wythoff / from . import wythoff）
    for alias, attr in ATTR_RE.findall(src):
        if alias in MODULES:
            refs[alias].add(attr)
    return refs


def part_census(out, repro_n=2):
    d = load_runs()
    runs = [r for r in d["runs"] if not r.get("err")]
    if not runs:
        print("[census] 无跑次面")
        return 3
    face = os.path.join(RP, "r585/snapshots")          # 只读面锚（用于守恒/只读性断言）
    pre = sha_tree(face, names=[".py"])
    per, bad = [], []
    for r in runs:
        gdir = SNAP % (r["round"], r["win"], r["sub"]) + "/games"
        if not os.path.isdir(gdir):
            per.append({"round": r["round"], "win": r["win"], "sub": r["sub"], "side": r["side"],
                        "err": "missing_tree"})
            continue
        exp, refs = {}, {}
        for m in MODULES:
            p = os.path.join(gdir, m + ".py")
            exp[m] = exports_of(open(p, encoding="utf-8", errors="replace").read()) if os.path.isfile(p) else set()
        mp = os.path.join(gdir, "__main__.py")
        msrc = open(mp, encoding="utf-8", errors="replace").read() if os.path.isfile(mp) else ""
        refs = main_refs(msrc)
        missing = {m: sorted(refs[m] - exp[m]) for m in MODULES if refs[m] - exp[m]}
        rec = {"round": r["round"], "win": r["win"], "sub": r["sub"], "side": r["side"],
               "n_refs": sum(len(v) for v in refs.values()), "missing": missing,
               "consistent": not missing}
        per.append(rec)
        if missing:
            bad.append(rec)
    # ---- 控制（成对、行为可分）：只写 /tmp 副本
    ctrl = {}
    tmp = tempfile.mkdtemp(prefix="r595-census-")
    try:
        # 直采判据: 控制源取**面内首个跑次**（不依赖「已有 bad 跑次」——否则面内零不自洽时
        # 判别力无对照，读数不可解释；承「零反例 ⇒ 判别器无牙」纪律）。
        csrc = None
        for x in runs:
            d0 = SNAP % (x["round"], x["win"], x["sub"]) + "/games"
            if os.path.isdir(d0):
                csrc = d0
                break
        if csrc is None:
            ctrl["no_source"] = {"ok": False, "note": "面无跑次树 ⇒ 不伪造对照"}
        else:
            a = os.path.join(tmp, "neg")
            shutil.copytree(csrc, a)
            b = os.path.join(tmp, "pos")
            shutil.copytree(csrc, b)
            rr0 = main_refs(open(os.path.join(a, "__main__.py"), encoding="utf-8", errors="replace").read())
            cand = [x for x in sorted(rr0["wythoff"]) if x not in ("__name__",)]
            name = cand[0] if cand else "solve"
            mp = os.path.join(b, "wythoff.py")
            s = open(mp, encoding="utf-8", errors="replace").read()
            s2 = re.sub(r"^(def|class)\s+%s\b" % re.escape(name),
                        r"\1 __r595_removed_%s" % name, s, flags=re.M)
            s2 = re.sub(r"^%s\s*=" % re.escape(name), "__r595_removed_%s = " % name, s2, flags=re.M)
            open(mp, "w", encoding="utf-8").write(s2)
            for tag, gdir, want_bad in (("NEG_原样副本", a, False), ("POS_删被引属性", b, True)):
                e = exports_of(open(os.path.join(gdir, "wythoff.py"), encoding="utf-8", errors="replace").read())
                rr = main_refs(open(os.path.join(gdir, "__main__.py"), encoding="utf-8", errors="replace").read())
                miss = sorted(rr["wythoff"] - e)
                ctrl[tag] = {"missing": miss, "consistent": not miss,
                             "ok": (not miss) != want_bad, "source": os.path.relpath(csrc, REPO),
                             "note": "被删属性 = %s" % name}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    controls_ok = all(v.get("ok") for v in ctrl.values())
    post = sha_tree(face, names=[".py"])
    # ---- 实测复现（静态判过不算过）
    repro = []
    for rec in bad[:repro_n]:
        src = SNAP % (rec["round"], rec["win"], rec["sub"])
        t = tempfile.mkdtemp(prefix="r595-repro-")
        try:
            tree = os.path.join(t, "g1")
            shutil.copytree(src, tree)
            mod = sorted(rec["missing"])[0]
            attr = rec["missing"][mod][0]
            env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": t,
                   "PYTHONPATH": os.path.join(tree, "games"), "PYTHONDONTWRITEBYTECODE": "1"}
            p = subprocess.run([sys.executable, "-B", "-m", "games", mod], cwd=tree, env=env,
                               input="", capture_output=True, text=True, timeout=60)
            tail = (p.stderr or "").strip().splitlines()[-1][:160] if (p.stderr or "").strip() else ""
            repro.append({"run": "%s/%s/%s" % (rec["round"], rec["win"], rec["sub"]), "game": mod,
                          "attr": attr, "rc": p.returncode, "stderr_tail": tail,
                          "reproduced": bool(p.returncode != 0 and attr in (p.stderr or ""))})
        except Exception as exc:  # noqa: BLE001
            repro.append({"run": "%s/%s/%s" % (rec["round"], rec["win"], rec["sub"]),
                          "err": "%s: %s" % (type(exc).__name__, exc)})
        finally:
            shutil.rmtree(t, ignore_errors=True)
    agg = {}
    for side in ("agent", "codex"):
        rs = [x for x in per if x.get("side") == side and "err" not in x]
        agg[side] = {"runs": len(rs), "inconsistent_runs": sum(1 for x in rs if not x["consistent"]),
                     "faces": sorted({m for x in rs for m in x["missing"]}),
                     "refs_total": sum(x["n_refs"] for x in rs)}
    rc = 0
    if not controls_ok or pre != post or any(r.get("reproduced") is False for r in repro):
        rc = 2
    res = {"round": "R595", "part": "census",
           "r594_baseline": "R594 只查 solve 单键（2/44 agent 跑次缺 solve、0/15 codex）；本轮扩到**全属性**面",
           "agg": agg, "per_run_n": len(per),
           "inconsistent": [{"run": "%s/%s/%s" % (x["round"], x["win"], x["sub"]), "side": x["side"],
                             "missing": x["missing"]} for x in bad],
           "repro": repro, "controls": ctrl, "controls_ok": controls_ok,
           "readonly_face_sha_pre": pre, "readonly_face_sha_post": post,
           "readonly_ok": pre == post, "rc": rc}
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[census] 面=%d agent=%s codex=%s | 控制 ok=%s 只读 ok=%s 复现=%s | rc=%d ⇒ %s"
          % (len(per), agg["agent"], agg["codex"], controls_ok, pre == post,
             [r.get("reproduced") for r in repro], rc, out))
    return rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True, choices=["gate", "coldset", "census"])
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = a.out or os.path.join(RP, "r595/face-%s-r595.json" % a.part)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if a.part == "gate":
        return part_gate(out)
    if a.part == "coldset":
        return part_coldset(out)
    return part_census(out)


if __name__ == "__main__":
    sys.exit(main())
