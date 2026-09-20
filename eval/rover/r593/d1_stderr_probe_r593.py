#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R593 追加只读探针：把 `D1_empty_or_error / nonzero_rc` 的 66 例次**定因到具体失败形态**。

只读（快照副本上重放同一 case 输入）+ 零产品改动；对每个 (跑次, 用例) 重跑一次，
捕获 rc / stderr 尾行 / 输出长度，并按**机械规则**归形态族（异常类型 + 消息首词，禁人工判读）。
器具自检：重跑必须复现产物侧登记的 rc≠0 与空正文（否则判 rc=2 = 器具缺陷）。
"""
import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile

REPO = "/home/agentuser/AgentFramework"
SRCJ = os.path.join(REPO, "eval/rover/r593/landing-predicate-r593.json")
OUT = os.path.join(REPO, "eval/rover/r593/d1-stderr-probe-r593.json")
CASES = os.path.join(REPO, "eval/rover/r591/cases/cases-r521.json")
ROUND_TREE = {"r585": "eval/rover/r585/snapshots", "r586": "eval/rover/r586/snapshots",
              "r587": "eval/rover/r587/snapshots", "r588": "eval/rover/r588/snapshots",
              "r591": "eval/rover/r591/snapshots"}


def run_one_err(tree, game, stdin, timeout):
    """v2.run_one 的**同语义**变体：唯一差别 = 同时返回 stderr（定因需要）。
    超时判 rc=124 + 空正文（与 v2 逐字同口径），因此重放可逐例与产物侧 rc 对账。"""
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": tree,
           "PYTHONPATH": tree, "PYTHONDONTWRITEBYTECODE": "1"}
    p = subprocess.Popen([sys.executable, "-B", "-m", "games", game], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                         cwd=tree, env=env, start_new_session=True)
    try:
        out, err = p.communicate(stdin, timeout=timeout)
        return (out or ""), (err or ""), p.returncode
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except Exception:  # noqa: BLE001
            pass
        try:
            p.communicate(timeout=5)
        except Exception:  # noqa: BLE001
            pass
        return "", "", 124
    except Exception:  # noqa: BLE001
        return "", "", -1


def shape_of(rc, err, out):
    """机械归形态族：只看末行异常类名 / 首词 / rc，禁人工判读。"""
    if rc == 124:
        return "TIMEOUT_60s", "timeout", ""
    tail = [l for l in (err or "").strip().splitlines() if l.strip()]
    last = tail[-1].strip() if tail else ""
    m = re.search(r"^([A-Za-z_][A-Za-z0-9_.]*Error|SystemExit|KeyboardInterrupt|"
                  r"[A-Za-z_][A-Za-z0-9_.]*Exception|[A-Za-z_][A-Za-z0-9_.]*Exit)\b", last)
    if m:
        kind = m.group(1)
        head = last.split(":", 1)[0].strip()
        detail = (last.split(":", 1)[1].strip()[:60] if ":" in last else "")
        return "%s|%s" % (kind, detail[:24]), head, last[:160]
    if "Traceback (most recent call last)" in (err or ""):
        return "TRACEBACK_NO_CLASS", "Traceback", last[:160]
    if rc != 0 and not (err or "").strip():
        return ("NONZERO_SILENT", "silent", "")
    if rc == 0 and not out.strip():
        return "RC0_EMPTY", "", ""
    return "OTHER", "", last[:160]


def main():
    d = json.load(io.open(SRCJ, encoding="utf-8"))
    cases = json.load(io.open(CASES, encoding="utf-8"))
    by_stdin = {}
    for c in cases:
        if c["game"] == "wythoff":
            by_stdin[c["stdin"].strip()] = c
    tmp = tempfile.mkdtemp(prefix="r593d1-")
    fams, rows, mismatch = {}, [], 0
    for r in d["runs"]:
        if "err" in r or r["side"] != "agent":
            continue
        hits = [x for x in r["failures"] if x.get("d_sub") == "D1_empty_or_error"]
        if not hits:
            continue
        src = os.path.join(REPO, ROUND_TREE[r["round"]], r["win"], r["sub"], "g1")
        tree = os.path.join(tmp, "%s-%s-%s" % (r["round"], r["win"], r["sub"]))
        if os.path.isdir(tree):
            shutil.rmtree(tree)
        shutil.copytree(src, tree)
        for x in hits:
            tout, terr, trc = run_one_err(tree, "wythoff", x["stdin"], 60)
            fam, head, last = shape_of(trc, terr, tout)
            fams[fam] = fams.get(fam, 0) + 1
            if (trc != 0) != (x["rc"] != 0) or bool(tout.strip()) != bool(x["got"]):
                mismatch += 1
            rows.append({"round": r["round"], "win": r["win"], "sub": r["sub"], "idx": x["idx"],
                         "stdin": x["stdin"], "class": x["class"], "rc": trc,
                         "out_len": len(tout), "family": fam, "head": head, "tail": last,
                         "src_rc": x["rc"], "src_got": x["got"]})
    shutil.rmtree(tmp, ignore_errors=True)
    out = {"round": "R593", "probe": "d1_stderr_probe", "target": "D1_empty_or_error / nonzero_rc",
           "n_replayed": len(rows), "failing_families": fams,
           "family_rank": sorted(fams.items(), key=lambda kv: -kv[1]),
           "replay_consistency": {"mismatch": mismatch, "rc_equal": mismatch == 0},
           "examples": rows[:6], "rows": rows}
    with io.open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("重放例次 %d | 复现不一致 %d | 形态族 %d 个" % (len(rows), mismatch, len(fams)))
    for k, v in out["family_rank"]:
        print("  %5d  %s" % (v, k))
    for e in rows[:6]:
        print("   例 %s %s idx=%s rc=%s tail=%s" % (e["round"], e["win"], e["idx"], e["rc"], e["tail"][:110]))
    return 0 if mismatch == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
