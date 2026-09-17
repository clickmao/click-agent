#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R528 · 归档产物树的**布局漂移**普查 (机检, 只读归档 + 临时目录实跑)。

问题 (R528 定因): R525 w3 两侧 agent 臂判 0/58, 被读成「产物不可运行/能力不足」。
逐调用取证显示: 该臂 8 调用 / 3 步把 `games/` 包写到 `<工作根>/sols/games_pkg/games/`,
随后 `cd sols/games_pkg && python3 -m games life` 自验通过 ⇒ 自认完成; 而验收形态是
**工作根**下 `python3 -m games <id>` ⇒ 前置器 0/58。

本器回答: **归档里有多少「失败」其实是布局漂移而非代码缺陷** —— 对每棵被判树:
  1. `layout_ok`: `<T>/games/__main__.py` 存在 (题面相对路径成立);
  2. 否则全树找名为 `games` 的包的入口 ⇒ 得到「真能跑起来的那层目录」`R` (相对 T);
     在临时副本里以 cwd=R 跑同一隐藏用例脚本 ⇒ 记 `code_ok` (代码本身对/错);
     分类 `layout_drift_code_ok` / `layout_drift_code_bad`;
  3. 全树没有任何 `games/<...>.py` ⇒ `missing_artifacts`。

判据 (预注册): ① 每棵被判树的分类必须唯一落在上述四类之一 (Σ == 扫到的树数);
② `layout_ok` 的树在**T 根**实跑必须 58/58 (自证扫法正确, 即扫法不是恒假);
③ 至少一棵 `layout_drift_code_ok` ⇒ 证伪「0/58 ⇒ 代码缺陷」的归因 (本轮核心结论的机检依据)。
只读归档 (禁改归档树); 副本一律落 /tmp。
"""
import argparse
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = "/home/agentuser/AgentFramework"
CASE_SCRIPT = os.path.join(REPO, "eval/rover/r523/cases/run_cases_r521.py")
SUM_RE = re.compile(r"^R521_CASES (\d+)/(\d+)$", re.M)
EXCLUDE_DIRS = {"__pycache__", "obj", "bin"}


def rel(p):
    r = os.path.relpath(p, REPO)
    return r if not r.startswith("..") else p


def walk_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for f in filenames:
            yield os.path.join(dirpath, f)


def find_package_dirs(root):
    """返回全树里「名为 games 且含 __main__.py」的包目录 (绝对路径)。"""
    out = []
    for f in walk_files(root):
        if os.path.basename(f) == "__main__.py" and os.path.basename(os.path.dirname(f)) == "games":
            out.append(os.path.dirname(f))
    return sorted(set(out))


def run_cases(cwd):
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    p = subprocess.run([sys.executable, "-I", "-B", CASE_SCRIPT], cwd=cwd, env=env,
                       capture_output=True, text=True, timeout=600)
    m = SUM_RE.search(p.stdout or "")
    if not m:
        return None, (p.stdout or "")[-200:] + (p.stderr or "")[-200:]
    return int(m.group(1)), "%s/%s" % (m.group(1), m.group(2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", default="eval/rover/r519/snapshots:"
                                       "eval/rover/r521/snapshots:"
                                       "eval/rover/r523/snapshots:"
                                       "eval/rover/r524/snapshots:"
                                       "eval/rover/r525/snapshots")
    ap.add_argument("--out", default="eval/rover/r528/layout-census.json")
    ap.add_argument("--expect-cases", type=int, default=58)
    a = ap.parse_args()

    trees = []
    for r in a.roots.split(":"):
        base = os.path.join(REPO, r)
        if not os.path.isdir(base):
            continue
        for win in sorted(os.listdir(base)):
            wp = os.path.join(base, win)
            if not os.path.isdir(wp):
                continue
            for arm in sorted(os.listdir(wp)):
                ap_ = os.path.join(wp, arm)
                if not os.path.isdir(ap_):
                    continue
                for tid in sorted(os.listdir(ap_)):
                    tp = os.path.join(ap_, tid)
                    if os.path.isdir(tp):
                        trees.append((r.split("/")[2], win, arm, tid, tp))

    rows = []
    for rnd, win, arm, tid, tp in trees:
        pkgs = find_package_dirs(tp)
        toplevel = os.path.join(tp, "games")
        row = {"round": rnd, "window": win, "arm": arm, "tid": tid, "tree": rel(tp),
               "n_pkg_dirs": len(pkgs)}
        if os.path.isfile(os.path.join(toplevel, "__main__.py")):
            row["class"] = "layout_ok"
            n, why = run_cases(tp)
            row["cases_root"] = n if n is not None else why
            row["code_ok"] = (n == a.expect_cases)
        elif pkgs:
            pkg = pkgs[0]
            runcwd = os.path.dirname(pkg)                      # `-m games` 生效的那层
            tmp = tempfile.mkdtemp(prefix="r528census-")
            dst = os.path.join(tmp, "tree")
            shutil.copytree(tp, dst, ignore=shutil.ignore_patterns("__pycache__"))
            n, why = run_cases(os.path.join(dst, os.path.relpath(runcwd, tp)))
            shutil.rmtree(tmp, ignore_errors=True)
            row["class"] = "layout_drift_code_ok" if n == a.expect_cases else "layout_drift_code_bad"
            row["drift_depth"] = os.path.relpath(runcwd, tp)
            row["cases_at_drift_dir"] = n if n is not None else why
            row["code_ok"] = (n == a.expect_cases)
        else:
            row["class"] = "missing_artifacts"
            row["code_ok"] = False
        rows.append(row)
        print("%-6s %-4s %-9s %-3s %-22s %s" % (rnd, win, arm, tid, row["class"],
                                                 row.get("drift_depth", "")), flush=True)

    classes = {}
    for r in rows:
        classes[r["class"]] = classes.get(r["class"], 0) + 1
    ok_root = [r for r in rows if r["class"] == "layout_ok"]
    doc = {
        "round": "R528",
        "what": "归档产物树布局漂移普查 (只读归档 + /tmp 副本实跑)",
        "case_script": rel(CASE_SCRIPT),
        "trees_scanned": len(rows),
        "classes": classes,
        "checks": {
            "C1_分类唯一且全计": sum(classes.values()) == len(rows),
            "C2_layout_ok树根实跑全对": all(r["code_ok"] for r in ok_root) if ok_root else None,
            "C3_漂移中代码正确数": sum(1 for r in rows
                                       if r["class"] == "layout_drift_code_ok"),
        },
        "rows": rows,
    }
    out = os.path.join(REPO, a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print("SUM trees=%d classes=%s checks=%s" % (len(rows), classes, doc["checks"]))
    print("OUT %s" % rel(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
