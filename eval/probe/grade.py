#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""随机能力自检判定器 (R398 长期任务)

判定铁律
--------
1. **只认隐藏用例**: 公开用例从不参与判定 ⇒ "硬编码公开样例"的解法必然暴露。
2. **失败必须分类**: 只报"通过率"是空心指标; 必须给出失败模式分布 (no_code / syntax /
   runtime / timeout / wrong / partial), 否则无法归因、无法沉淀经验。
3. **判定器自身必须过负控**: 判定器若被注入"跳过比对"这类缺陷, 必须变红
   (见 `--selftest` 末三条反向负控)。判据不能自证。
4. **语言无关判据**: 判据 = (stdin, stdout) 二元关系; 沙箱只负责执行。

用法
----
    python3 eval/probe/grade.py --selftest
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

PY = sys.executable or "python3"
FENCE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.S)
FINAL = re.compile(r"FINAL\s*:\s*(\S+)")

SANDBOX_ENV = {
    "PYTHONIOENCODING": "utf-8",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
    "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    "LC_ALL": "C.UTF-8",
}


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ARTIFACT = re.compile(r"(?:\./)?data/artifacts/(py_[0-9a-f]+\.py)")
REPLY_MARK = "── 回复"


def _compiles(src: str) -> bool:
    try:
        compile(src, "<probe>", "exec")
        return True
    except SyntaxError:
        return False


def _prefixes(text: str):
    """由长到短逐行截断 (取最长可编译前缀): CLI 回复区尾部会混入状态行。"""
    lines = (text or "").rstrip().split("\n")
    for k in range(len(lines), 0, -1):
        yield "\n".join(lines[:k])


def candidates(reply: str, since: float = None) -> list:
    """候选程序, 按产品真实交付形态多路收集 (真机教训 R398):
       ① 显式围栏代码块  ② CLI 回复区裸代码  ③ 回复中给出的落盘产物路径 (可加新鲜度门槛)
    """
    text = reply or ""
    out = [b.strip("\n") for b in FENCE.findall(text)]
    idx = text.find(REPLY_MARK)
    if idx >= 0:
        seg = text[idx:].split("\n", 1)
        if len(seg) > 1 and seg[1].strip():
            out.append(seg[1].strip("\n"))
    for m in ARTIFACT.finditer(text):
        path = os.path.join(ROOT, m.group(0).lstrip("./"))
        if not os.path.exists(path):
            continue
        if since is not None and os.path.getmtime(path) + 1.0 < since:
            continue
        with open(path, encoding="utf-8") as fh:
            out.append(fh.read().strip("\n"))
    return out


def extract_code(reply: str, since: float = None) -> str:
    """抽候选程序: 多路候选里取**第一个可编译**的; 都不可编译则返回最长者 (此时 syntax_error 才是真失败)。"""
    cands = [c for c in candidates(reply, since) if c and c.strip()]
    if not cands:
        return ""
    for c in sorted(cands, key=len, reverse=True):
        if _compiles(c):
            return c
        for pre in _prefixes(c):
            if _compiles(pre):
                return pre
    return max(cands, key=len)


def extract_final(reply: str) -> str:
    hits = FINAL.findall(reply or "")
    return hits[-1].strip().strip("`.,;") if hits else ""


def run_code(code: str, stdin_text: str, timeout: float = 5.0) -> dict:
    """在隔离临时目录里跑候选程序。返回 {stdout, exit, timed_out, err}。"""
    work = tempfile.mkdtemp(prefix="probe_")
    try:
        src = os.path.join(work, "sol.py")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(code)
        try:
            p = subprocess.run([PY, "-I", "-B", src], input=stdin_text,
                               capture_output=True, text=True, timeout=timeout,
                               cwd=work, env=SANDBOX_ENV)
        except subprocess.TimeoutExpired:
            return {"stdout": "", "exit": -9, "timed_out": True, "err": "timeout"}
        except OSError as e:  # 解释器缺失等环境性问题: 显式出声, 不静默算失败
            return {"stdout": "", "exit": -1, "timed_out": False, "err": "oserror: %s" % e}
        return {"stdout": p.stdout, "exit": p.returncode, "timed_out": False,
                "err": (p.stderr or "")[-400:]}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def norm(text: str) -> str:
    """输出比对归一: 去行尾空白 + 去末尾空行 (只容忍空白差异, 不容忍内容差异)。"""
    lines = [ln.rstrip() for ln in (text or "").replace("\r\n", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _syntax_ok(code: str) -> bool:
    try:
        compile(code, "<sol>", "exec")
        return True
    except SyntaxError:
        return False


def grade_program(task: dict, reply: str, timeout: float = 5.0) -> dict:
    """返回 {mode, passed, total, detail[], taxonomy}。mode ∈ 上面铁律 2 的集合。"""
    code = extract_code(reply)
    if not code or not code.strip():
        return {"mode": "no_code", "passed": 0, "total": len(task["hidden"]),
                "detail": [], "taxonomy": {"no_code": 1}}
    if not _syntax_ok(code):
        return {"mode": "syntax_error", "passed": 0, "total": len(task["hidden"]),
                "detail": [], "taxonomy": {"syntax_error": 1}}

    tax, detail = {}, []
    for i, case in enumerate(task["hidden"]):
        r = run_code(code, case["stdin"], timeout)
        if r["timed_out"]:
            v = "timeout"
        elif r["exit"] != 0:
            v = "runtime_error"
        elif norm(r["stdout"]) == norm(case["expected_stdout"]):
            v = "ok"
        else:
            v = "wrong_output"
        tax[v] = tax.get(v, 0) + 1
        detail.append({"case": i, "verdict": v,
                       "got": norm(r["stdout"])[:120], "want": norm(case["expected_stdout"])[:120]})
    passed = tax.get("ok", 0)
    total = len(task["hidden"])
    mode = "ok" if passed == total else ("timeout" if "timeout" in tax else
                                        "runtime_error" if "runtime_error" in tax else
                                        "partial" if passed else "wrong_output")
    return {"mode": mode, "passed": passed, "total": total, "detail": detail, "taxonomy": tax}


def grade_math(task: dict, reply: str) -> dict:
    got = extract_final(reply)
    want = task["answer"]
    if not got:
        return {"mode": "no_final", "passed": 0, "total": 1, "detail": [], "taxonomy": {"no_final": 1}}
    ok = got == want or (got.lstrip("+") == want)
    return {"mode": "ok" if ok else "wrong_final", "passed": 1 if ok else 0, "total": 1,
            "detail": [{"case": 0, "verdict": "ok" if ok else "wrong_final", "got": got, "want": want}],
            "taxonomy": {"ok" if ok else "wrong_final": 1}}


def grade(task: dict, reply: str, timeout: float = 5.0) -> dict:
    return grade_program(task, reply, timeout) if task["kind"] == "program" else grade_math(task, reply)


# ---------------------------------------------------------------- 负控

_GOOD_MAXSUB = """
import sys
d=sys.stdin.read().split()
n=int(d[0]); a=[int(x) for x in d[1:1+n]]
best=cur=a[0]
for x in a[1:]:
    cur=max(x,cur+x); best=max(best,cur)
print(best)
"""

_BAD_OFFBYONE = _GOOD_MAXSUB.replace("print(best)", "print(best-1)")   # 真差一: 输出必错
assert _BAD_OFFBYONE != _GOOD_MAXSUB
_BAD_LOOP = "while True:\n    pass\n"
_BAD_SYNTAX = "def f(:\n    pass\n"


def _mk_program_task():
    return {"kind": "program", "family": "max_subarray",
            "hidden": [{"stdin": "3\n1 -2 3\n", "expected_stdout": "3"},
                       {"stdin": "4\n-1 -2 -3 -4\n", "expected_stdout": "-1"}]}


def selftest() -> int:
    ok, fails = 0, []

    def chk(name, cond, detail=""):
        nonlocal ok
        if cond:
            ok += 1
            print("  [PASS] %s %s" % (name, detail))
        else:
            fails.append(name)
            print("  [FAIL] %s %s" % (name, detail))

    t = _mk_program_task()
    print("selftest: 判定器正控 / 负控")

    r = grade_program(t, "```python\n%s\n```" % _GOOD_MAXSUB)
    chk("正控: 正确解判满分", r["mode"] == "ok" and r["passed"] == 2, str(r["taxonomy"]))

    r = grade_program(t, "")
    chk("负控: 无代码块判 no_code", r["mode"] == "no_code")

    r = grade_program(t, "先分析一下…\n```python\n%s\n```\n完成" % _BAD_SYNTAX)
    chk("负控: 语法错判 syntax_error", r["mode"] == "syntax_error")

    r = grade_program(t, "```python\n%s\n```" % _BAD_LOOP, timeout=1.0)
    chk("负控: 死循环判 timeout", r["mode"] == "timeout")

    r = grade_program(t, "```python\n%s\n```" % _BAD_OFFBYONE)
    chk("负控: 差一错误判 wrong_output", r["mode"] == "wrong_output",
        "passed=%d/%d" % (r["passed"], r["total"]))

    # 只过公开用例的作弊解: 硬编码公开样例 ⇒ 隐藏用例必挂
    cheat = "print(3)" if t["hidden"][0]["expected_stdout"] == "3" else "print(0)"
    r = grade_program(t, "```python\n%s\n```" % cheat)
    chk("负控: 单值硬编码判部分/错", r["passed"] < 2, "passed=%d/2" % r["passed"])

    r = grade_program({"kind": "program", "hidden": t["hidden"]}, "```python\n%s\n```" % _GOOD_MAXSUB)
    chk("正控: 与公开用例无关(判定只用隐藏)", r["passed"] == 2)

    tm = {"kind": "math", "family": "comb_mod", "answer": "5"}
    chk("正控: math FINAL 解析", grade_math(tm, "推导…\nFINAL: 5")["mode"] == "ok")
    chk("负控: math 无 FINAL 判 no_final", grade_math(tm, "答案是 5")["mode"] == "no_final")
    chk("负控: math 错答判 wrong_final", grade_math(tm, "FINAL: 6")["mode"] == "wrong_final")

    # ---- 真机形态负控 (R398 首轮真跑抓到的两个判定器缺陷, 固化为永久负控)
    cli_like = "── 执行中 (turn 1) ──\n  [05] PY 落盘\n── 回复 ──\n%s\n  [06] 收尾状态行" % _GOOD_MAXSUB
    r = grade_program(t, cli_like)
    chk("负控: 无围栏 CLI 回复+尾部状态行 ⇒ 仍能抽到可编译前缀",
        r["mode"] == "ok" and r["passed"] == 2, str(r["taxonomy"]))

    import tempfile as _tf
    global ROOT
    real_root = ROOT
    td = _tf.mkdtemp(prefix="probe_art_")
    art = os.path.join(td, "data/artifacts")
    os.makedirs(art, exist_ok=True)
    name = "py_deadbeef00.py"
    with open(os.path.join(art, name), "w", encoding="utf-8") as fh:
        fh.write(_GOOD_MAXSUB)
    try:
        ROOT = td
        r = grade_program(t, "已写入 ./data/artifacts/%s (2026B) ✓ py_compile" % name)
        chk("正控: 回复只给产物路径 ⇒ 读产物判分", r["passed"] == 2, str(r["taxonomy"]))
        r = grade_program(t, "", since=10 ** 12)
        chk("负控: 空回复判 no_code", r["mode"] == "no_code")
    finally:
        ROOT = real_root

    # ---- 判定器自身反向负控: 把比对函数换成恒真, 正向负控必须转红
    global norm
    real_norm = norm
    norm = lambda text: ""  # noqa: E731  恒等: 任何输出都算相等 ⇒ 差一错误解将"变成"正确
    try:
        r = grade_program(t, "```python\n%s\n```" % _BAD_OFFBYONE)
        chk("反向负控: 比对恒真时差一解被误判为通过 (证明判据非空心)",
            r["mode"] == "ok", "mode=%s" % r["mode"])
    finally:
        norm = real_norm

    r = grade_program(t, "```python\n%s\n```" % _BAD_OFFBYONE)
    chk("反向负控: 比对恢复后差一解再次被抓", r["mode"] == "wrong_output")

    print("selftest %d/%d" % (ok, ok + len(fails)))
    return 0 if not fails else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
