#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R597 候选③ 器具: 交付物的**行为面**契约普查（只读源 / 有界子进程 / 零产品改动）。

背景（R595 器具自捕 ③）: R595 的**静态**属性普查在交付物 `importlib` 动态派发下**结构性无牙**
（POS 控制不翻面）⇒ 本轮改口径: 不看源码属性，直接**实跑**交付物的入口契约
`python3 -B -m games <family>`（4 族），记录 rc + stderr 类别。

判类（预注册 C9，**跑前**写死）:
  OK         : rc=0
  ENTRY_FAIL : stderr 命中 {ModuleNotFoundError, ImportError, AttributeError('module … has no attribute …')}
               ⇒ **交付面/契约面不自治**（R594 已把「缺入口」定因到产物侧契约自相矛盾）
  INTERNAL   : stderr 命中其它异常名（IndexError/TypeError/ValueError/RecursionError/…）⇒ 产物内部错
  TIMEOUT    : >TMO 秒未退出（有界，进程组收口）

读法: 跑次级（run-level）ENTRY_FAIL 计数（任一族命中即计该跑次），两侧（agent / codex）分列；
与 R594 的 `solve` 单键面、R595 的静态面**并列**（禁相减）。

控制（成对 + 有界）:
  POS: 在**副本**上把 `games/<family>.py` 改名 ⇒ 该族必须判 ENTRY_FAIL（否则普查无牙）
  NEG: 同一副本**原样** ⇒ 该族必须判 OK
  收口: 全部子进程 `start_new_session=True` + `killpg`；结束后断言残留 = 0（承 R592 孤儿教训）

用法: python3 eval/rover/r596/behav_census_r596.py [--out eval/rover/r596/behav-census-r596.json]
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile

REPO = "/home/agentuser/AgentFramework"
FAM = ("life", "nim", "sub", "wythoff")
SCOPE = {"r585": ["w154", "w155", "w156"], "r586": ["w157", "w158", "w159"],
         "r587": ["w160", "w161", "w162"], "r588": ["w163", "w164", "w165"],
         "r591": ["w166", "w167", "w168"], "r595": ["w169", "w170", "w171"],
         "r596": ["w172", "w173", "w174"], "r597": ["w175", "w176", "w177"]}
SUBS = ("agentD-r1", "agentD-r2", "agentD-r3", "codex")
TMO = 10.0
CASE_JSON = os.path.join(REPO, "eval/rover/r596/cases/cases-r521.json")


def sha12(p: str) -> str:
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()[:12]


def tree_stamp(root: str) -> str:
    """目录指纹（逐文件 sha256 累积；用于只读性断言 —— 任何写都会改它）。"""
    h = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for fn in sorted(filenames):
            fp = os.path.join(dirpath, fn)
            h.update(os.path.relpath(fp, root).encode())
            try:
                h.update(io.open(fp, "rb").read())
            except OSError:
                h.update(b"<unreadable>")
    return h.hexdigest()[:12]


def classify(rc: int, err: str, timed_out: bool) -> str:
    if timed_out:
        return "TIMEOUT"
    if rc == 0:
        return "OK"
    if ("ModuleNotFoundError" in err or "ImportError" in err
            or ("AttributeError" in err and "has no attribute" in err)):
        return "ENTRY_FAIL"
    if any(x in err for x in ("IndexError", "TypeError", "ValueError", "KeyError", "RecursionError",
                              "ZeroDivisionError", "NameError", "AttributeError", "FileNotFoundError")):
        return "INTERNAL"
    return "OTHER_RC"


def probe(tree: str, stdin_by_fam: dict) -> dict:
    """对一棵产物树实跑 4 族入口；返回 {family: {cls, rc, err_head}}。"""
    out = {}
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": tree,
           "PYTHONPATH": tree, "PYTHONDONTWRITEBYTECODE": "1"}
    for f in FAM:
        p = None
        try:
            p = subprocess.Popen([sys.executable, "-B", "-m", "games", f], cwd=tree, env=env,
                                 stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                 text=True, start_new_session=True)
            try:
                _, err = p.communicate(input=stdin_by_fam.get(f, ""), timeout=TMO)
                cls = classify(p.returncode, err or "", False)
                out[f] = {"cls": cls, "rc": p.returncode, "err_head": (err or "").strip().splitlines()[-1][:160] if err else ""}
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(p.pid), signal.SIGKILL)
                except Exception:  # noqa: BLE001
                    pass
                out[f] = {"cls": "TIMEOUT", "rc": None, "err_head": "TIMEOUT_%ds" % int(TMO)}
        except Exception as e:  # noqa: BLE001
            out[f] = {"cls": "SPAWN_FAIL", "rc": None, "err_head": type(e).__name__}
        finally:
            if p is not None:
                try:
                    p.stdout and p.stdout.close()
                except Exception:  # noqa: BLE001
                    pass
    return out


def load_stdin_by_fam() -> dict:
    cases = json.load(io.open(CASE_JSON, encoding="utf-8"))
    out = {}
    for c in cases:
        out.setdefault(c["game"], c["stdin"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r596/behav-census-r596.json"))
    ap.add_argument("--scope-rounds", default=",".join(SCOPE))
    a = ap.parse_args()
    rounds = [r for r in a.scope_rounds.split(",") if r]
    stdin_by_fam = load_stdin_by_fam()
    scratch = tempfile.mkdtemp(prefix="r597-census-")
    issues, rows = [], {}
    stamp_before = {p: tree_stamp(p) for p in
                    [os.path.join(REPO, "eval/rover", r, "snapshots") for r in rounds
                     if os.path.isdir(os.path.join(REPO, "eval/rover", r, "snapshots"))]}
    for rnd in rounds:
        for win in SCOPE.get(rnd, []):
            for sub in SUBS:
                snap = os.path.join(REPO, "eval/rover", rnd, "snapshots", win, sub, "g1")
                if not os.path.isdir(snap):
                    issues.append({"why": "snapshot_missing", "round": rnd, "win": win, "sub": sub})
                    continue
                dst = os.path.join(scratch, "%s-%s-%s" % (rnd, win, sub))
                shutil.copytree(snap, dst)
                res = probe(dst, stdin_by_fam)
                shutil.rmtree(dst, ignore_errors=True)
                rows["%s/%s/%s" % (rnd, win, sub)] = res
    # ---- 控制（成对, 副本上做）----
    good = None
    for k, v in rows.items():
        if all(x["cls"] == "OK" for x in v.values()):
            good = k
            break
    ctrl = {"base_run": good}
    if good:
        rnd, win, sub = good.split("/")
        src = os.path.join(REPO, "eval/rover", rnd, "snapshots", win, sub, "g1")
        d1 = os.path.join(scratch, "pos")
        shutil.copytree(src, d1)
        fam = FAM[0]
        os.rename(os.path.join(d1, "games", fam + ".py"), os.path.join(d1, "games", fam + "_x.py"))
        pos = probe(d1, stdin_by_fam)
        shutil.rmtree(d1, ignore_errors=True)
        d2 = os.path.join(scratch, "neg")
        shutil.copytree(src, d2)
        neg = probe(d2, stdin_by_fam)
        shutil.rmtree(d2, ignore_errors=True)
        ctrl.update({"pos_family": fam, "pos_cls": pos[fam]["cls"], "pos_err": pos[fam]["err_head"],
                     "pos_has_teeth": pos[fam]["cls"] == "ENTRY_FAIL",
                     "neg_cls": neg[fam]["cls"], "neg_clean": neg[fam]["cls"] == "OK"})
    # ---- 汇总 ----
    def side_of(k: str) -> str:
        return "codex" if k.endswith("codex") else "agent"
    summ = {"agent": {"runs": 0, "ENTRY_FAIL": 0, "INTERNAL": 0, "TIMEOUT": 0, "OK": 0, "OTHER": 0},
            "codex": {"runs": 0, "ENTRY_FAIL": 0, "INTERNAL": 0, "TIMEOUT": 0, "OK": 0, "OTHER": 0}}
    fam_hist = {}
    entry_fail_runs = []
    for k, v in sorted(rows.items()):
        s = summ[side_of(k)]
        s["runs"] += 1
        classes = [x["cls"] for x in v.values()]
        for c in classes:
            fam_hist[c] = fam_hist.get(c, 0) + 1
        top = ("ENTRY_FAIL" if "ENTRY_FAIL" in classes else
               "TIMEOUT" if "TIMEOUT" in classes else
               "INTERNAL" if "INTERNAL" in classes else
               "OTHER" if any(c not in ("OK",) for c in classes) else "OK")
        s[top if top in s else "OTHER"] = s.get(top if top in s else "OTHER", 0) + 1
        if "ENTRY_FAIL" in classes:
            entry_fail_runs.append({"run": k, "families": [f for f, x in v.items() if x["cls"] == "ENTRY_FAIL"],
                                    "err": next(x["err_head"] for x in v.values() if x["cls"] == "ENTRY_FAIL")})
    stamp_after = {p: tree_stamp(p) for p in stamp_before}
    readonly_ok = stamp_before == stamp_after
    strays = [l for l in subprocess.run(["ps", "-eo", "args"], capture_output=True, text=True).stdout.splitlines()
              if scratch in l and "-m games" in l]
    shutil.rmtree(scratch, ignore_errors=True)
    rc = 0 if (ctrl.get("pos_has_teeth") and ctrl.get("neg_clean") and readonly_ok and not strays and not issues) else 2
    out = {"round": "R596", "candidate": "③ 交付物行为面契约普查（替代 R595 静态面无牙版）",
           "instrument_sha12": sha12(os.path.abspath(__file__)),
           "scope": {"rounds": rounds, "runs": len(rows), "families": list(FAM), "timeout_s": TMO,
                     "stdin_source": os.path.relpath(CASE_JSON, REPO), "stdin_sha12": sha12(CASE_JSON)},
           "per_run": rows, "summary": summ, "family_class_hist": fam_hist,
           "entry_fail_runs": entry_fail_runs, "controls": ctrl,
           "readonly": {"snapshot_stamp_equal": readonly_ok, "strays": len(strays)},
           "issues": issues,
           "verdict": {"rc": rc,
                       "agent_entry_fail_share": round(summ["agent"]["ENTRY_FAIL"] / max(1, summ["agent"]["runs"]), 4),
                       "codex_entry_fail_share": round(summ["codex"]["ENTRY_FAIL"] / max(1, summ["codex"]["runs"]), 4),
                       "note": "行为面普查 ≠ 能力验收；跑次横跨 7 轮窗集 ⇒ 非独立样本；与 R594 单键面/R595 静态面并列"}}
    with io.open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("== R597 候选③ 行为面普查 ==")
    print("跑次=%d | 类别直方图: %s" % (len(rows), json.dumps(fam_hist, ensure_ascii=False)))
    print("agent: %s" % json.dumps(summ["agent"], ensure_ascii=False))
    print("codex: %s" % json.dumps(summ["codex"], ensure_ascii=False))
    print("ENTRY_FAIL 跑次 %d 个: %s" % (len(entry_fail_runs), json.dumps(entry_fail_runs, ensure_ascii=False)[:400]))
    print("控制: base=%s POS 有牙=%s NEG 干净=%s | 只读=%s 残留=%d | rc=%d"
          % (ctrl.get("base_run"), ctrl.get("pos_has_teeth"), ctrl.get("neg_clean"), readonly_ok, len(strays), rc))
    return rc


if __name__ == "__main__":
    sys.exit(main())
