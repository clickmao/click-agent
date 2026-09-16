#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比数据**可验收前置**：两侧产出物必须 ① 可实际执行 ② 正确（用户 2026-09-17 令）。

规则（本轮落为宪法级前置）: 与 codex 的对照读数，只有**两侧产出物都真的能跑、且跑出来是对的**，
才构成「可验收对比数据」；否则该轮读数一律记 NOT_VERIFIABLE，不得当作验收依据。

与 `judge_contrast_r5xx.py` 的分工: 判据器吃**已落盘摘要**（判分器内部跑过一遍）；本器具走
**独立执行路径** —— 把产出物**物化到磁盘**（artifact 文件原样复制 / transcript 代码落盘），
再用 `python3 -I -B <file>` + 逐条 hidden 用例 stdin 实跑，比对规范化 stdout。

用法:
  python3 eval/rover/r507pre/exec_precondition.py \
      --taskset eval/rover/r504/taskset-r504.json \
      --codex data/probe/probe-cmd:....json --agent data/probe/probe-agent-...json \
      --out eval/rover/r507pre/precondition-r504.json
退出码: 0 = 可验收（两侧全跑通且全对）; 1 = 不可验收（点名）; 3 = 输入缺失 fail-closed
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"
sys.path.insert(0, os.path.join(REPO, "eval/probe"))
import grade  # noqa: E402

PY = sys.executable


def load(p):
    return json.load(io.open(p, encoding="utf-8-sig"))


def reply_text(paths):
    for p in paths or []:
        ap = p if os.path.isabs(p) else os.path.join(REPO, p)
        if os.path.isfile(ap):
            return io.open(ap, encoding="utf-8", errors="replace").read()
    return ""


def materialize(code, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write(code)
    return path


def run_file(path, stdin_text, timeout=10.0):
    try:
        p = subprocess.run([PY, "-I", "-B", path], input=(stdin_text or "").encode("utf-8"),
                           capture_output=True, timeout=timeout, cwd=os.path.dirname(path))
        return {"rc": p.returncode, "stdout": p.stdout.decode("utf-8", "replace"),
                "stderr_tail": p.stderr.decode("utf-8", "replace")[-200:]}
    except subprocess.TimeoutExpired:
        return {"rc": 124, "stdout": "", "stderr_tail": "TIMEOUT"}
    except Exception as e:  # pragma: no cover
        return {"rc": 125, "stdout": "", "stderr_tail": str(e)[:200]}


def check_side(side, summary, tasks, work, timeout=10.0):
    rows = []
    for t in summary.get("per_task") or []:
        tid = t.get("tid")
        task = tasks.get(tid)
        if task is None:
            rows.append({"tid": tid, "status": "task_not_in_taskset"})
            continue
        kind = task.get("kind")
        art = [a for a in (t.get("artifacts") or []) if a]
        rep = reply_text(t.get("reply_paths"))
        code = grade.extract_code(rep, None, art)
        rec = {"tid": tid, "kind": kind, "family": task.get("family"),
               "graded_mode": t.get("mode"), "code_source": t.get("code_source"),
               "artifact_on_disk": bool(art and os.path.isfile(art[0])),
               "code_chars": len(code or "")}
        if kind != "program":
            # 无「可执行」面: 只记判定器的正确性结论（不冒充执行读数）
            rec.update({"exec": "not-applicable", "correct": t.get("mode") == "ok",
                        "note": "非程序题(kind=%s): 无执行面, 只核正确性" % kind})
            rows.append(rec)
            continue
        if not code or not code.strip():
            rec.update({"exec": "no_code", "correct": False})
            rows.append(rec)
            continue
        fp = materialize(code, os.path.join(work, "%s-%s.py" % (side, tid)))
        pub = (task.get("public") or [{}])[0]
        e = run_file(fp, pub.get("stdin"), timeout)
        rec["exec_rc_public"] = e["rc"]
        rec["exec"] = "ok" if e["rc"] == 0 else "rc=%s" % e["rc"]
        cases = []
        for i, c in enumerate(task.get("hidden") or []):
            r = run_file(fp, c.get("stdin"), timeout)
            ok = (r["rc"] == 0) and (grade.norm(r["stdout"]) == grade.norm(c.get("expected_stdout")))
            cases.append(ok)
        rec.update({"cases_n": len(cases), "cases_pass": sum(1 for x in cases if x),
                    "correct": bool(cases) and all(cases), "path": fp})
        rows.append(rec)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--taskset", required=True)
    ap.add_argument("--codex", required=True)
    ap.add_argument("--agent", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--timeout", type=float, default=10.0)
    a = ap.parse_args()
    for p in (a.taskset, a.codex, a.agent):
        if not os.path.isfile(p):
            print("[致命] 输入缺失: %s ⇒ fail-closed rc=3" % p)
            return 3
    ts = load(a.taskset)
    tasks = {t["tid"]: t for t in ts}
    work = "/tmp/r507pre"
    os.makedirs(work, exist_ok=True)
    out = {"label": a.label, "taskset": a.taskset, "tasks_n": len(tasks),
           "rule": "对比数据可验收前置: 两侧产出物须可实际执行且正确 (用户 2026-09-17 令)", "sides": {}}
    for side, path in (("codex", a.codex), ("agent", a.agent)):
        rows = check_side(side, load(path), tasks, work, a.timeout)
        prog = [r for r in rows if r.get("kind") == "program"]
        out["sides"][side] = {
            "summary": path,
            "program_tasks": len(prog),
            "exec_ok": sum(1 for r in prog if r.get("exec") == "ok"),
            "correct_n": sum(1 for r in prog if r.get("correct")),
            "rows": rows,
        }
    bad = []
    for side, s in out["sides"].items():
        for r in s["rows"]:
            if r.get("kind") == "program" and (r.get("exec") != "ok" or not r.get("correct")):
                bad.append("%s/%s exec=%s correct=%s cases=%s/%s" %
                           (side, r["tid"], r.get("exec"), r.get("correct"),
                            r.get("cases_pass"), r.get("cases_n")))
    out["executable_and_correct"] = not bad
    out["blocked"] = bad
    io.open(a.out, "w", encoding="utf-8", newline="\n").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    for side, s in out["sides"].items():
        print("%-6s program=%d exec_ok=%d correct=%d" % (side, s["program_tasks"], s["exec_ok"], s["correct_n"]))
        for r in s["rows"]:
            if r.get("kind") == "program":
                print("   %-5s %-24s graded=%-8s exec=%-6s cases=%s/%s correct=%s src=%s" %
                      (r["tid"], r.get("family"), r.get("graded_mode"), r.get("exec"),
                       r.get("cases_pass"), r.get("cases_n"), r.get("correct"), r.get("code_source")))
            else:
                print("   %-5s %-24s (kind=%s) correct=%s" % (r["tid"], r.get("family"), r.get("kind"), r.get("correct")))
    print("EXECUTABLE_AND_CORRECT=%s" % out["executable_and_correct"])
    if bad:
        print("BLOCKED: " + " | ".join(bad))
    print("OUT=" + a.out)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
