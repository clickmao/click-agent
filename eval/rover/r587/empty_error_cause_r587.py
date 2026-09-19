#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R587 · 只读定因 ②: `EMPTY_OR_ERROR` 族（空产物 / 非零 rc）是否与「产物未交付」同源。

零产品改动 / 零新夹具 / 零远端 —— 冻结快照**副本**上重放（不污染冻结树）。

工序:
  逐 (轮, 窗, 臂) 复制快照到临时目录 -> 逐 wythoff 用例 `python3 -m games <game>` (stdin=用例输入)
  -> 记录 rc / stdout 长度 / stderr 首行 + 异常类型（traceback 末行）
分类（机械）:
  TRACEBACK_<ExcType>  非零 rc 且 stderr 含 traceback ⇒ 崩溃（记录异常类型 + 末行源码）
  EMPTY_RC0            rc=0 且 stdout 为空/空白 ⇒ 静默空产物
  NONEMPTY_RC0_FAIL    有输出但非期望（形态错，不属本族）
  TIMEOUT              超时
自证有牙（负控）:
  · 正控: 在**已知全过**的产物拷贝（`--control-ok`）上必须 0 例非零 rc / 0 例空产物;
  · 负控: 在**已知空产物**的产物拷贝（`--control-bad`）上必须 >=1 例本族命中;
  两侧都成对才算分类器有牙（否则读数作废, 记 has_teeth=false）。
用法:
  python3 eval/rover/r587/empty_error_cause_r587.py [--rounds r586] [--out <path>]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = "/home/agentuser/AgentFramework"
CASES = os.path.join(REPO, "eval/rover/r586/cases/cases-r521.json")
EXC_RE = re.compile(r"^(\w+(?:Error|Exception|Warning))\b", re.M)


def load_cases():
    allc = json.load(io.open(CASES, encoding="utf-8"))
    return [(i, c) for i, c in enumerate(allc) if c["game"] == "wythoff"]


def replay(win, arm, rk, cases, timeout=25):
    src = os.path.join(REPO, "eval/rover", rk, "snapshots", win, arm, "g1")
    if not os.path.isdir(src):
        return None, "missing_snapshot:%s" % src
    # 臂级缺产物 ≠ 例级崩溃: 产物树里没有 `games/` ⇒ 该臂**未交付产物**(臂级), 不入例级分类
    if not os.path.isfile(os.path.join(src, "games", "wythoff.py")) and \
       not os.path.isdir(os.path.join(src, "games")):
        return None, "NO_ARTIFACT(臂级: 工作区无 games/ ⇒ 未交付产物; 由产物面数落盘数另行断言)"
    tmp = tempfile.mkdtemp(prefix="r587-empty-")
    dst = os.path.join(tmp, "copy")
    shutil.copytree(src, dst)
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": dst,
           "PYTHONPATH": dst, "PYTHONDONTWRITEBYTECODE": "1"}
    rows = []
    for i, c in cases:
        try:
            p = subprocess.run([sys.executable, "-m", "games", c["game"]], input=c["stdin"],
                               capture_output=True, text=True, cwd=dst, env=env, timeout=timeout)
            rc, out, err = p.returncode, p.stdout, p.stderr
        except subprocess.TimeoutExpired:
            rows.append({"idx": i, "class": "TIMEOUT", "rc": None, "out_len": 0, "exc": None, "stderr_first": ""})
            continue
        errf = (err or "").strip().splitlines()
        excs = EXC_RE.findall(err or "")
        # 本族外 = 有输出(判对/判错不在本器具的判据面) ⇒ 标签必须**不带 FAIL 字样**
        # （R587 器具缺陷: 初版叫 `NONEMPTY_RC0_FAIL`, 被下游 join 当失败族计 ⇒ 「每个形态族都失败」的假信号;
        #  语义=「不属本族」, 更名 `NONEMPTY_RC0_OTHER`; 本轮已落盘件的旧标签名由 join 显式白名单排除）
        cls = "NONEMPTY_RC0_OTHER"
        if rc != 0:
            cls = ("TRACEBACK_" + excs[-1]) if excs else "RC_NONZERO_NO_TRACEBACK"
        elif not (out or "").strip():
            cls = "EMPTY_RC0"
        rows.append({"idx": i, "class": cls, "rc": rc, "out_len": len((out or "").strip()),
                     "exc": excs[-1] if excs else None,
                     "stderr_first": (errf[-1][:160] if errf else "")})
    shutil.rmtree(tmp, ignore_errors=True)
    return rows, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", default="r586")
    ap.add_argument("--control-ok", default="w157/agentD-r2")     # 已知 15/15 全过
    ap.add_argument("--control-bad", default="w159/agentD-r2")    # 已知 15/15 EMPTY_OR_ERROR
    ap.add_argument("--control-round", default="r586")
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r587/empty-error-cause-r587.json"))
    a = ap.parse_args()
    cases = load_cases()

    # ── 自证有牙: 两侧成对控制 ────────────────────────────────────────────────
    _cw, _ca = a.control_ok.split("/")
    _bw, _ba = a.control_bad.split("/")
    okr, okerr = replay(win=_cw, arm=_ca, rk=a.control_round, cases=cases)
    badr, baderr = replay(win=_bw, arm=_ba, rk=a.control_round, cases=cases)
    fam = ("EMPTY_RC0", "TIMEOUT")
    ok_bad = 0 if not okr else len([r for r in okr if r["class"] in fam or r["rc"] not in (0, None)])
    bad_bad = 0 if not badr else len([r for r in badr if r["class"] in fam or r["rc"] not in (0, None)])
    teeth = (okr is not None and badr is not None and ok_bad == 0 and bad_bad >= 1)

    per, fam_rows = {}, []
    for rk in a.rounds.split(","):
        sroot = os.path.join(REPO, "eval/rover", rk, "snapshots")
        if not os.path.isdir(sroot):
            continue
        for win in sorted(os.listdir(sroot)):
            wd = os.path.join(sroot, win)
            if not os.path.isdir(wd):
                continue
            for arm in sorted(os.listdir(wd)):
                if not os.path.isdir(os.path.join(wd, arm, "g1")):
                    continue
                rows, err = replay(win, arm, rk, cases)
                key = "%s|%s|%s" % (rk, win, arm)
                if rows is None:
                    per[key] = {"err": err}
                    continue
                cnt = {}
                for r in rows:
                    cnt[r["class"]] = cnt.get(r["class"], 0) + 1
                    if r["class"] in fam or (r["rc"] not in (0, None)):
                        fam_rows.append({"round": rk, "win": win, "arm": arm, **r})
                per[key] = {"classes": cnt, "n": len(rows)}

    # 同源判据: 本族命中的**异常类型 + 末行**是否单一（单一 ⇒ 与「产物未交付」同源: 同一缺陷行）
    exc_hist = {}
    for r in fam_rows:
        k = "%s | %s" % (r["class"], (r["exc"] or "-"))
        exc_hist[k] = exc_hist.get(k, 0) + 1
    out = {
        "round": "R587",
        "instrument": "eval/rover/r587/empty_error_cause_r587.py",
        "mode": "read_only (冻结快照副本上重放; 零产品改动 / 零新夹具 / 零远端)",
        "control": {"ok": {"copy": a.control_ok, "n_family": ok_bad, "err": okerr},
                    "bad": {"copy": a.control_bad, "n_family": bad_bad, "err": baderr},
                    "has_teeth": teeth,
                    "note": "两侧成对: 全过产物 0 例本族 ∧ 空产物产物 >=1 例本族 才算分类器有牙"},
        "per_copy": per,
        "family_rows": fam_rows,
        "n_family_rows": len(fam_rows),
        "exception_histogram": exc_hist,
        "single_source": (len(exc_hist) == 1),
    }
    json.dump(out, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"has_teeth": teeth, "control_ok_n": ok_bad, "control_bad_n": bad_bad,
                      "n_family_rows": len(fam_rows), "exception_histogram": exc_hist},
                     ensure_ascii=False, indent=1))
    return 0 if teeth else 1


if __name__ == "__main__":
    raise SystemExit(main())
