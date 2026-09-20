#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R592 — wythoff 失分只读定因器 **v2**（修 v1 成对控制无牙；只修器具，不放宽任何判据/阈值）。

v1 = `eval/rover/r591/landing_predicate_r591.py`（读数 rc=2 / has_teeth=false ⇒ 层结论不入结论）。
本轮先用 `probe_v1_defect_r592.py` **量出** v1 的三处缺陷（先量再改），再修：

  D1 **序约定错配（比较域不对称的真身）**: oracle 冷集存 `(max,min)` 序 `[(2,1),(5,3),…]`，
     而行为探针网格只有 `a≤b` 的 `(1,2),(3,5),…` ⇒ `C_prod` 与 `C_true` **恒**产生 9/9 对称差
     ⇒ `cold_set_equal` 恒 False、层 (b) 恒被选中（v1 实测层分布 12/12=(b)；POS 夹具也因此永不可能判 (a)）。
  D2 **分层单条件**: 跑次级分层只用 `C_prod == C_true` ⇒ 与「落点谓词取反」的真身无关 ⇒ 控制无牙。
  D3 **错误并入冷集**: 网格输出只分 WIN / 非 WIN ⇒ 非法或空输出被并入「声明冷集」。

v2 修法（器具面）:
  ① 冷集一律 `canon = (min,max)` 归一后比较（域统一；oracle 与网格两侧都过 canon）。
  ② 网格输出三分: WIN / LOSE / ERROR；**只有 LOSE 计入产物声明冷集**，ERROR 单列计数。
  ③ 分层改为**两个行为信号**的机械组合（真值只进 B 信号）:
     `V_land>0`  ⟺ 产物给出的着法**落点不在它自己声明的冷集内**（内部不闭合） ⇒ **(a) 落点/选择谓词层**
     `V_land==0 ∧ C_prod!=C_true` ⇒ **(b) 冷集构造层**（自洽但与真值不同）
     `V_land==0 ∧ C_prod==C_true` ⇒ **(c) 本轴外**（本轴两信号皆无）
     `V_int`（声明冷集在**真 Wythoff 着法关系**下是否独立）单列**诊断**，不作分层触发（见下）。
  ④ 控制三件且**行为可分**（v1 的 NEG 夹具「冷集删一个位置」在行为上与正确实现**等价** ⇒ 不可作控制）:
     `OK`  = 真值冷集 + 正确落点逻辑 + lexmin 选点 ⇒ 期望 `C_prod==C_true` ∧ `V_land==0` ∧ 无 wythoff 失分
     `POS` = 真值冷集 + 落点谓词取反 ⇒ 期望层 (a)
     `NEG` = **Nim 式信念**（冷集 = 对角线 xor-zero + 单堆取子着法集）⇒ 对自己的着法集自洽 ⇒ 期望层 (b)
  ⑤ 子进程 `start_new_session=True` + 超时 `os.killpg` 收**进程组**（v1 只杀直接子进程 ⇒ 父进程被杀后
     子进程成孤儿继续吃核：R591 实测 2 个孤儿各 ~95% CPU 存活 66–90 min）；收尾残留扫描必须 = 0（fail-closed）。

判据（预注册 `eval/rover/r592/prereg-r592.json`）: C1 控制三件全中 ⇒ has_teeth=true，否则 rc=2；
C2 非平凡（真实跑次形态 ≥2 个互异）；C5 残留进程 == 0；C6 只读性。**不放宽、不事后调阈值。**

用法: python3 eval/rover/r592/landing_predicate_r592.py [--out ...] [--jobs 8] [--rounds r585,r586,r587,r588,r591]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

REPO = "/home/agentuser/AgentFramework"
CASES = os.path.join(REPO, "eval/rover/r591/cases/cases-r521.json")
SRC562 = os.path.join(REPO, "eval/rover/r562/wythoff_cause_r562.py")
ROUNDS = ["r585", "r586", "r587", "r588", "r591"]
L = 25
CASE_TIMEOUT = 60
GRID_TIMEOUT = 10


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def canon(p):
    return (min(p), max(p))


def legal_moves(a, b):
    """真 Wythoff 着法集: 单堆取 k 或两堆同取 k（k≥1）。"""
    mv = []
    for k in range(1, a + 1):
        mv.append((k, 0))
    for k in range(1, b + 1):
        mv.append((0, k))
    for k in range(1, min(a, b) + 1):
        mv.append((k, k))
    return mv


def run_one(tree, game, stdin, timeout):
    """子进程按**进程组**收口（v2 修复点 ⑤）。"""
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": tree,
           "PYTHONPATH": tree, "PYTHONDONTWRITEBYTECODE": "1"}
    p = subprocess.Popen([sys.executable, "-B", "-m", "games", game], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                         cwd=tree, env=env, start_new_session=True)
    try:
        out, _err = p.communicate(stdin, timeout=timeout)
        return out or "", p.returncode
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except Exception:  # noqa: BLE001
            pass
        try:
            p.communicate(timeout=5)
        except Exception:  # noqa: BLE001
            pass
        return "", 124
    except Exception:  # noqa: BLE001
        return "", -1


WIN_RE = re.compile(r"^WIN\s+(\d+)\s+(\d+)\s*$")


def probe_grid(tree, positions, jobs):
    def one(p):
        a, b = p
        out, rc = run_one(tree, "wythoff", "%d %d\n" % (a, b), GRID_TIMEOUT)
        s = out.strip()
        m = WIN_RE.match(s)
        if m:
            return p, ("WIN", int(m.group(1)), int(m.group(2))), rc, s[:40]
        if s == "LOSE":
            return p, ("LOSE", None, None), rc, s[:40]
        return p, ("ERROR", None, None), rc, s[:40]
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        return list(ex.map(one, positions))


def discover(rounds, include_codex=False):
    runs = []
    for r in rounds:
        root = os.path.join(REPO, "eval/rover", r, "snapshots")
        if not os.path.isdir(root):
            continue
        for win in sorted(os.listdir(root)):
            for sub in sorted(os.listdir(os.path.join(root, win))):
                if not include_codex and not sub.startswith("agentD"):
                    continue
                g1 = os.path.join(root, win, sub, "g1")
                if os.path.isdir(os.path.join(g1, "games")):
                    runs.append({"round": r, "win": win, "sub": sub, "src": g1})
    return runs


FIX_BODY = {
    # 冷集构造器: mex 递推（= 真值）；NIM 变体用对角线
    "mex": ("def _cold_positions(n):\n"
            "    cold = {(0, 0)}\n    taken = {0}\n    i = 1\n    while True:\n"
            "        a = i\n        while a in taken:\n            a += 1\n        b = a + i\n"
            "        if b > n:\n            break\n        cold.add((a, b))\n        cold.add((b, a))\n"
            "        taken.add(a)\n        taken.add(b)\n        i += 1\n    return cold\n\n\n"),
    "diag": ("def _cold_positions(n):\n"
             "    cold = set()\n    for k in range(0, n + 1):\n        cold.add((k, k))\n    return cold\n\n\n"),
}
LEX = ("def _pick(a, b, cold, moves):\n"
       "    cand = []\n"
       "    for i, j in moves:\n"
       "        if (max(a - i, b - j), min(a - i, b - j)) in cold:\n"
       "            cand.append((i, j))\n"
       "    return min(cand) if cand else None\n\n\n")


def synth_fixture(kind, dst):
    """OK = 正确实现; POS = 落点谓词取反; NEG = Nim 式信念（对角线冷集 + 单堆着法）。"""
    os.makedirs(os.path.join(dst, "games"), exist_ok=True)
    io.open(os.path.join(dst, "games", "__init__.py"), "w").close()
    if kind == "OK":
        body = (FIX_BODY["mex"] + LEX +
                "def solve(text):\n"
                "    a, b = map(int, text.split()[:2])\n"
                "    cold = _cold_positions(max(a, b))\n"
                "    mv = [(k, 0) for k in range(1, a + 1)] + [(0, k) for k in range(1, b + 1)] + "
                "[(k, k) for k in range(1, min(a, b) + 1)]\n"
                "    p = _pick(a, b, cold, mv)\n"
                "    return ('LOSE' if p is None else 'WIN %d %d' % p)\n")
    elif kind == "POS":
        body = (FIX_BODY["mex"] +
                "def solve(text):\n"
                "    a, b = map(int, text.split()[:2])\n"
                "    cold = _cold_positions(max(a, b))\n"
                "    for k in range(1, max(a, b) + 1):\n"
                "        for mv in ((k, 0), (0, k), (k, k)):\n"
                "            i, j = mv\n"
                "            if i > a or j > b:\n"
                "                continue\n"
                "            t = (max(a - i, b - j), min(a - i, b - j))\n"
                "            if t not in cold:\n"                       # 落点谓词取反 ⇒ 层 (a)
                "                return 'WIN %d %d' % (i, j)\n"
                "    return 'LOSE'\n")
    else:  # NEG：Nim 式信念（对角冷集 + 只能单堆取子）⇒ 对自己着法集自洽、但声明冷集非真值 ⇒ 层 (b)
        body = (FIX_BODY["diag"] +
                "def solve(text):\n"
                "    a, b = map(int, text.split()[:2])\n"
                "    cold = _cold_positions(max(a, b))\n"
                "    for k in range(1, a + 1):\n"
                "        if (max(a - k, b), min(a - k, b)) in cold:\n"
                "            return 'WIN %d %d' % (k, 0)\n"
                "    for k in range(1, b + 1):\n"
                "        if (max(a, b - k), min(a, b - k)) in cold:\n"
                "            return 'WIN %d %d' % (0, k)\n"
                "    return 'LOSE'\n")
    with io.open(os.path.join(dst, "games", "wythoff.py"), "w") as fh:
        fh.write(body)
    with io.open(os.path.join(dst, "games", "__main__.py"), "w") as fh:
        fh.write("import sys\nfrom . import wythoff\nif __name__ == '__main__':\n"
                 "    print(wythoff.solve(sys.stdin.read()))\n")


def analyse_run(run, cases, ora, jobs, tmp):
    tree = os.path.join(tmp, "run-%s-%s-%s" % (run["round"], run["win"], run["sub"]))
    if os.path.isdir(tree):
        shutil.rmtree(tree)
    shutil.copytree(run["src"], tree)
    # ① 例级重放（分类器 import r562，禁重写第二份）
    wy = [c for c in cases if c["game"] == "wythoff"]
    out = []
    for i, c in enumerate(wy):
        got, rc = run_one(tree, "wythoff", c["stdin"], CASE_TIMEOUT)
        cls, extra = ora["classify"](c, got, rc, ora["ora"])
        out.append({"idx": i, "stdin": c["stdin"].strip(), "exp": c["expected_stdout"].strip(),
                    "got": got.strip()[:40], "class": cls, "detail": extra})
    # ② 全网格行为探针（三分）→ 产物**声明**冷集
    positions = [(a, b) for a in range(0, L + 1) for b in range(a, L + 1)]
    grid = probe_grid(tree, positions, jobs)
    c_prod, n_win, n_err, err_samples = set(), 0, 0, []
    win_moves = {}
    for p, res, rc, raw in grid:
        if res[0] == "LOSE":
            c_prod.add(p)
        elif res[0] == "WIN":
            n_win += 1
            i, j = res[1], res[2]
            win_moves[p] = (i, j, canon((p[0] - i, p[1] - j)))
        else:
            n_err += 1
            if len(err_samples) < 5:
                err_samples.append({"pos": list(p), "raw": raw, "rc": rc})
    c_true = {canon(p) for p in ora["cold"] if max(p) <= L}
    only_prod = sorted(c_prod - c_true)
    only_true = sorted(c_true - c_prod)
    set_equal = (c_prod == c_true)
    # ③ 行为信号
    v_land = []        # 着法落点 ∉ 自身声明冷集（内部不闭合）⇒ (a)
    for p, (i, j, t) in sorted(win_moves.items()):
        if (i, j) == (0, 0) or i < 0 or j < 0:
            continue
        if not ((i > 0 and j == 0) or (i == 0 and j > 0) or (i == j)):
            continue           # 非法着法归 D 桶（不参与落点信号）
        if t not in c_prod:
            v_land.append({"pos": list(p), "move": [i, j], "target": list(t)})
    v_int = []         # 声明冷集在真 Wythoff 着法关系下不独立（诊断项，非分层触发）
    for p in sorted(c_prod):
        for (i, j) in legal_moves(p[0], p[1]):
            if canon((p[0] - i, p[1] - j)) in c_prod:
                v_int.append({"pos": list(p), "target": list(canon((p[0] - i, p[1] - j)))})
                break
    if v_land:
        layer = "(a) 落点/选择谓词层"
    elif not set_equal:
        layer = "(b) 冷集构造层"
    else:
        layer = "(c) 本轴外"
    # ④ 逐失败例分桶（桶定义与 v1 逐字不变，保持可比）
    buckets, detail = {}, []
    for x in out:
        if x["class"] == "OK":
            continue
        b = None
        if x["class"] == "MOVE_NOT_COLD":
            m = re.search(r"target\((\d+),\s*(\d+)\)", x["detail"] or "")
            t = canon((int(m.group(1)), int(m.group(2)))) if m else None
            b = "A_landing_loose" if (t is not None and t not in c_prod) else "B_coldset"
        elif x["class"] == "WIN_FOR_LOSE":
            a0, b0 = [int(v) for v in x["stdin"].split()]
            got_m = WIN_RE.match(x["got"])
            if got_m:
                i, j = int(got_m.group(1)), int(got_m.group(2))
                t = canon((a0 - i, b0 - j))
                b = "B_coldset" if t in c_prod else "A_landing_loose"
            else:
                b = "D_delivery_or_shape"
        elif x["class"] == "LOSE_FOR_WIN":
            b = "B_coldset"
        elif x["class"] == "MOVE_NOT_LEXMIN":
            b = "A_selection_order"
        else:
            b = "D_delivery_or_shape"
        buckets[b] = buckets.get(b, 0) + 1
        detail.append(dict(x, bucket=b))
    return {"round": run["round"], "win": run["win"], "sub": run["sub"],
            "cases_pass_wythoff": sum(1 for x in out if x["class"] == "OK"), "cases_n": len(out),
            "declared_cold_n": len(c_prod), "grid_lose_n": len(c_prod), "grid_win_n": n_win, "grid_err_n": n_err,
            "grid_err_samples": err_samples,
            "cold_set_equal": bool(set_equal),
            "cold_only_prod": [list(p) for p in only_prod], "cold_only_true": [list(p) for p in only_true],
            "v_land_n": len(v_land), "v_land_samples": v_land[:5],
            "v_int_n": len(v_int), "v_int_samples": v_int[:5],
            "layer": layer, "buckets": buckets, "failures": detail}


def sha_tree(root):
    h = hashlib.sha256()
    for dp, dn, fn in os.walk(root):
        dn.sort()
        for f in sorted(fn):
            p = os.path.join(dp, f)
            h.update(os.path.relpath(p, root).encode())
            try:
                with open(p, "rb") as fh:
                    h.update(fh.read())
            except Exception:  # noqa: BLE001
                pass
    return h.hexdigest()


def audit_strays(kill=True):
    """扫宿主上 `-B -m games` 残留子进程（v2 修复点的成对判据）。"""
    found = []
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            with open("/proc/%s/cmdline" % pid, "rb") as fh:
                cl = fh.read().decode("utf-8", "replace").split("\x00")
        except Exception:  # noqa: BLE001
            continue
        if "-B" in cl and "-m" in cl and "games" in cl:
            found.append({"pid": int(pid), "cmd": " ".join(x for x in cl if x)})
    if found and kill:
        for f in found:
            try:
                os.kill(f["pid"], signal.SIGKILL)
            except Exception:  # noqa: BLE001
                pass
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r592/landing-predicate-r592.json"))
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--rounds", default=",".join(ROUNDS))
    ap.add_argument("--controls-only", action="store_true")
    a = ap.parse_args()
    rounds = [x.strip() for x in a.rounds.split(",") if x.strip()]
    m562 = load(SRC562, "we562")
    cases = json.load(io.open(CASES, encoding="utf-8"))
    ora_built = m562.build_oracle(cases)
    if not ora_built["fixture_agrees"]:
        raise SystemExit("冻结夹具与独立 oracle 不一致 ⇒ 夹具缺陷, 停")
    ora = {"cold": ora_built["cold"], "lexmin": ora_built["lexmin"],
           "phi_vs_brute_equal": ora_built["phi_vs_brute_equal"],
           "fixture_agrees": ora_built["fixture_agrees"],
           "classify": m562.classify,
           "ora": {"cold": ora_built["cold"], "lexmin": ora_built["lexmin"]}}
    strays_before = audit_strays()
    tmp = tempfile.mkdtemp(prefix="r592lp-")
    pre_sha = {r["round"] + "/" + r["win"] + "/" + r["sub"]: sha_tree(r["src"])
               for r in discover(rounds)}
    pre_sha["cases-r521.json"] = hashlib.sha256(open(CASES, "rb").read()).hexdigest()
    # 成对控制
    ctrl = {}
    for kind in ("OK", "POS", "NEG"):
        d = os.path.join(tmp, "ctrl-" + kind)
        synth_fixture(kind, d)
        r = analyse_run({"round": "ctrl", "win": "ctrl", "sub": kind, "src": d}, cases, ora, a.jobs, tmp)
        ctrl[kind] = {"layer": r["layer"], "cold_set_equal": r["cold_set_equal"],
                      "v_land_n": r["v_land_n"], "v_int_n": r["v_int_n"],
                      "declared_cold_n": r["declared_cold_n"], "grid_err_n": r["grid_err_n"],
                      "cases_pass_wythoff": r["cases_pass_wythoff"], "cases_n": r["cases_n"],
                      "buckets": r["buckets"]}
    ok_ok = (ctrl["OK"]["cold_set_equal"] and ctrl["OK"]["v_land_n"] == 0
             and ctrl["OK"]["cases_pass_wythoff"] == ctrl["OK"]["cases_n"])
    pos_a = ctrl["POS"]["layer"].startswith("(a)")
    neg_b = ctrl["NEG"]["layer"].startswith("(b)")
    has_teeth = bool(ok_ok and pos_a and neg_b)
    res = [] if a.controls_only else []
    if not a.controls_only:
        for r in discover(rounds):
            try:
                res.append(analyse_run(r, cases, ora, a.jobs, tmp))
            except Exception as e:  # noqa: BLE001
                res.append({"round": r["round"], "win": r["win"], "sub": r["sub"],
                            "err": "%s: %s" % (type(e).__name__, str(e)[:120])})
    ok = [r for r in res if "err" not in r]
    agg_b, lyr, forms = {}, {}, {}
    for r in ok:
        for k, v in r["buckets"].items():
            agg_b[k] = agg_b.get(k, 0) + v
        lyr[r["layer"]] = lyr.get(r["layer"], 0) + 1
        key = (r["cold_set_equal"], r["v_land_n"] > 0)
        forms["%s|v_land>0=%s" % ("equal" if key[0] else "diff", key[1])] = \
            forms.get("%s|v_land>0=%s" % ("equal" if key[0] else "diff", key[1]), 0) + 1
    # 非平凡性：控制臂三件必须**读数互异**（防「坏器具恒定输出」冒充确定性）。
    # controls-only 模式下轮次面为空 ⇒ 以控制臂形态为准；全量模式下两面都要成立。
    ctrl_forms = {}
    for k in ("OK", "POS", "NEG"):
        key = (ctrl[k]["cold_set_equal"], ctrl[k]["v_land_n"] > 0)
        ctrl_forms["%s|v_land>0=%s" % ("equal" if key[0] else "diff", key[1])] = \
            ctrl_forms.get("%s|v_land>0=%s" % ("equal" if key[0] else "diff", key[1]), 0) + 1
    non_trivial = len(ctrl_forms) >= 2 and (a.controls_only or len(forms) >= 2)
    shares = {k: round(v / max(1, sum(agg_b.values())), 4) for k, v in agg_b.items()}
    strays_after = audit_strays()
    post_sha = {k: (sha_tree(os.path.join(REPO, "eval/rover", k.split("/")[0], "snapshots",
                                          k.split("/")[1], k.split("/")[2], "g1"))
                    if k != "cases-r521.json" else hashlib.sha256(open(CASES, "rb").read()).hexdigest())
                for k in pre_sha}
    readonly_ok = (pre_sha == post_sha)
    # rc 语义分层（fail-closed、编码验收面）:
    #   0 = 器具可用（控制三件有牙 ∧ 非平凡 ∧ 无残留 ∧ 只读）；controls-only 模式即自检通过
    #   2 = 器具缺陷（控制无牙 / 读数恒定 / 残留子进程 / 冻结快照被改写）
    #   3 = 输入缺失或环境失败
    rc = 0
    if not has_teeth:
        rc = 2
    elif not non_trivial:
        rc = 2
    elif strays_after:
        rc = 2
    elif not readonly_ok:
        rc = 2
    elif not a.controls_only and len(ok) == 0:
        rc = 3
    out = {"round": "R592", "instrument": {"path": __file__, "version": "v2",
                                           "supersedes_criterion_readings": True,
                                           "v1": {"path": os.path.join(REPO, "eval/rover/r591/landing_predicate_r591.py"),
                                                  "verdict_rc": 2, "has_teeth": False,
                                                  "note": "v1 判定原样保留不翻案（器具缺陷: D1 序约定错配 / D2 分层单条件 / D3 错误并入冷集）"}},
           "scope": {"rounds": rounds, "runs_analysed": len(ok), "runs_total": len(res),
                     "grid_L": L, "positions": (L + 1) * (L + 2) // 2,
                     "oracle": {"phi_vs_brute_equal": ora["phi_vs_brute_equal"],
                                "fixture_agrees": ora["fixture_agrees"]}},
           "controls": ctrl,
           "negative_control": {"OK_ok": ok_ok, "POS_layer_a": pos_a, "NEG_layer_b": neg_b,
                                "has_teeth": has_teeth, "non_trivial_forms": non_trivial,
                                "forms": forms},
           "strays": {"before": strays_before, "after": strays_after},
           "readonly": {"pre": pre_sha, "post": post_sha, "ok": readonly_ok},
           "layer_by_run": lyr, "bucket_totals": agg_b, "bucket_shares": shares,
           "runs": res,
           "verdict": {"main_cause": (max(shares, key=lambda k: shares[k]) if shares else None),
                       "main_cause_rule": "份额 ≥50% 记主因, 否则记『无单主因』",
                       "layer_rule": "(a) v_land>0 / (b) v_land==0 ∧ C_prod!=C_true / (c) 两者皆无",
                       "rc": rc}}
    with io.open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("== R592 定因器 v2 ==")
    print("跑次 %d/%d (err=%d) | oracle 一致=%s" % (len(ok), len(res), len(res) - len(ok), ora["fixture_agrees"]))
    print("控制: OK=%s(eq=%s v_land=%d cases=%d/%d) POS=%s NEG=%s"
          % (ok_ok, ctrl["OK"]["cold_set_equal"], ctrl["OK"]["v_land_n"],
             ctrl["OK"]["cases_pass_wythoff"], ctrl["OK"]["cases_n"], ctrl["POS"]["layer"], ctrl["NEG"]["layer"]))
    print("has_teeth=%s 非平凡=%s 形态=%s" % (has_teeth, non_trivial, json.dumps(forms, ensure_ascii=False)))
    print("残留子进程: before=%d after=%d | 只读性=%s" % (len(strays_before), len(strays_after), readonly_ok))
    print("层分布: %s" % json.dumps(lyr, ensure_ascii=False))
    print("失败例次分桶: %s 份额: %s 主因=%s" % (json.dumps(agg_b, ensure_ascii=False),
                                             json.dumps(shares, ensure_ascii=False), out["verdict"]["main_cause"]))
    print("rc=%d" % rc)
    shutil.rmtree(tmp, ignore_errors=True)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
