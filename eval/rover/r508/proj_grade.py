#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R508 项目级判分器 (铁律 11 可验收前置)。

判据: 产物目录内 `python3 -I -B cases/{task}_cases.py` 逐条隐藏用例机械判对;
      用例脚本只驱动产物真实行为 (起服务/跑 CLI), 不读产物源码。
--isolate: 先把产物**独立物化**到全新临时目录再判 (判分不改动产物原地)。
全 PASS 且 rc=0 ⇒ all_pass=True ⇒ 该侧该题「可验收」。
"""
from __future__ import annotations
import argparse, json, os, re, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = {"p1": "cases/p1_cases.py", "p2": "cases/p2_cases.py", "p3": "cases/p3_cases.py"}
REF = {"p1": "ref/p1", "p2": "ref/p2", "p3": "ref/p3"}
CASE_RE = re.compile(r"^CASE (\S+) (PASS|FAIL)(?: (.*))?$")
MIN_ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8"}


def run_cases(task, workdir, timeout=420):
    script = os.path.join(HERE, CASES[task])
    t0 = time.time()
    env = dict(MIN_ENV)
    env["HOME"] = workdir
    p = subprocess.run([sys.executable, "-I", "-B", script], cwd=workdir,
                       capture_output=True, text=True, timeout=timeout, env=env)
    cases = []
    for ln in p.stdout.splitlines():
        m = CASE_RE.match(ln.strip())
        if m:
            cases.append({"name": m.group(1), "status": m.group(2), "detail": (m.group(3) or "")[:400]})
    all_pass = bool(cases) and p.returncode == 0 and all(c["status"] == "PASS" for c in cases)
    return {
        "task": task, "dir": workdir, "rc": p.returncode,
        "case_count": len(cases),
        "pass_count": sum(1 for c in cases if c["status"] == "PASS"),
        "all_pass": all_pass, "cases": cases,
        "elapsed_ms": int((time.time() - t0) * 1000),
        "stdout_tail": p.stdout[-1200:], "stderr_tail": p.stderr[-600:],
    }


def isolate(src):
    dst = tempfile.mkdtemp(prefix="r508-grade-")
    for name in os.listdir(src):
        s = os.path.join(src, name)
        d = os.path.join(dst, name)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks=False)
        elif os.path.isfile(s):
            shutil.copy2(s, d)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, choices=sorted(CASES))
    ap.add_argument("--dir", default=None, help="产物目录 (默认用 --oracle 取参考解)")
    ap.add_argument("--oracle", action="store_true", help="判参考解 (正控)")
    ap.add_argument("--isolate", action="store_true", help="先独立物化到全新临时目录再判")
    ap.add_argument("--json", default=None, help="结果落盘路径")
    ap.add_argument("--timeout", type=int, default=420)
    a = ap.parse_args()

    src = os.path.join(HERE, REF[a.task]) if a.oracle else a.dir
    if not src or not os.path.isdir(src):
        print(json.dumps({"error": "dir_not_found", "dir": src}, ensure_ascii=False))
        return 2
    target = isolate(src) if a.isolate else src
    res = run_cases(a.task, target, a.timeout)
    res["source_dir"] = os.path.abspath(src)
    res["isolated"] = bool(a.isolate)
    if a.json:
        os.makedirs(os.path.dirname(os.path.abspath(a.json)) or ".", exist_ok=True)
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k not in ("cases", "stdout_tail", "stderr_tail")}, ensure_ascii=False))
    for c in res["cases"]:
        print("  %-34s %-4s %s" % (c["name"], c["status"], c["detail"]))
    return 0 if res["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
