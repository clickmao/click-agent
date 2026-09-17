#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""删除引用闸 —— 减法批里的**删除**若仍被仓内代码/器具硬编码引用 ⇒ 红灯并逐条点名。

动因 (真实缺陷, 不是预防性机制):
    R534 减法批删除了 `eval/rover/r504/codex_solver_r504.py`, 而 `eval/rover/r508|r509|r511` 的
    `proj_run_side*.py` 里仍硬编码该路径 ⇒ 外侧(真值)臂在**静默**状态下不可执行("缺模块即不执行"),
    直到 R540 才被察觉。约定「减法批删除前必查跨轮调用点」只写在文档里 ⇒ 会被跳过 ⇒ 做成机械闸。

语义 (故意只覆盖**真危险面**):
    扫描面 = 可执行/可导入的代码与器具: .py .sh .bash .pyi .cs .csproj .ps1
    明确**不在**扫描面 (已知空洞, 不是漏判): 文档(*.md)、JSON/JSONL 台账(kpi.jsonl/registry/status/evidence)
        —— 台账里记删除是**应该**发生的, 拿它当引用点会变成噪声闸。
    引用 = 文本中出现被删文件的**仓内相对路径**或其 **basename**(basename 亦会被 `spec_from_file_location` 等紧耦合)。
    **只算「可执行的引用点」**: .py 走 AST, 取**字符串字面量**(排除 docstring); .sh/.cs 行级扫描跳过注释行。
    注释 / docstring 里的**叙述性提及**不算引用点(不执行)。这是**有意的语义收窄** —— R540 首次跑该闸时,
    历史回放被 6 处注释命中(含本轮自己写的因果注释) ⇒ '提及即红' 会变噪声闸; 但反过来它也是**已知空洞**:
    注释掉的调用点、字符串拼接出来的路径(如 "codex_solver_r50" + "4.py")抓不到。

用法:
    python3 tools/refactor/delete_ref_gate.py --staged            # 预提交(默认): 读 git diff --cached --diff-filter=D
    python3 tools/refactor/delete_ref_gate.py --file <path> ...   # 检查「若删除该文件」的引用面
    python3 tools/refactor/delete_ref_gate.py --selfcheck         # 正/负控自证 (在 /tmp 临时仓里做真删除+真引用)
    python3 tools/refactor/delete_ref_gate.py --staged --root <dir>
    公共: --json 机读输出
退出码: 0 = 无被引用的删除; 1 = 有 (红灯, 逐条点名 文件:行); 3 = 用法/环境错误
豁免: AGENTFRAMEWORK_DELREF_CHECK=0 (显式豁免; 报告里须记「本轮豁免了删除引用闸」)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

SCAN_PATHSPECS = ["*.py", "*.pyi", "*.sh", "*.bash", "*.cs", "*.csproj", "*.ps1"]
ENV_OFF = "AGENTFRAMEWORK_DELREF_CHECK"


def git(root: str, args: list[str]) -> tuple[int, str]:
    p = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def staged_deletions(root: str) -> list[str]:
    rc, out = git(root, ["diff", "--cached", "--name-only", "--diff-filter=D"])
    if rc != 0:
        raise RuntimeError("git diff 失败: " + out.strip()[:200])
    return [l.strip() for l in out.splitlines() if l.strip()]


def _py_live_strings(src: str) -> tuple[list[tuple[int, str]], str | None]:
    """只把**可执行的字符串字面量**当真引用点: 注释与 docstring 都不执行 ⇒ 不算调用点(有意收窄, 见模块头『已知空洞』)。
    返回 ([(行号, 字符串值)], 解析错误或 None)。"""
    import ast
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [], "SyntaxError(%s)" % e
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None) or []
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                docstrings.add(id(body[0].value))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
            out.append((node.lineno, node.value))
    return out, None


def _line_live_lines(src: str, ext: str) -> list[tuple[int, str]]:
    """非 .py: 行级扫描, 跳过注释行 (sh: #; cs/ps1: // 与 /* 与 *)。"""
    out = []
    for i, line in enumerate(src.splitlines(), 1):
        s = line.strip()
        if not s:
            continue
        if ext in (".sh", ".bash") and s.startswith("#"):
            continue
        if ext in (".cs", ".csproj", ".ps1") and (s.startswith("//") or s.startswith("/*") or s.startswith("*")):
            continue
        out.append((i, line))
    return out


def refs_for(root: str, path: str, exclude: set[str]) -> list[dict]:
    """返回引用点; 自指(被删文件自身/同批被删文件)不算引用。
    .py 用 AST 取可执行字符串字面量; 其余按行扫描跳过注释行。"""
    pats = [p for p in {path, os.path.basename(path)} if p]
    rc, out = git(root, ["grep", "-l", "-F", "-e", path, "-e", os.path.basename(path), "--", *SCAN_PATHSPECS])
    files = [l.strip() for l in out.splitlines() if l.strip()] if rc in (0, 1) else []
    hits: list[dict] = []
    for f in files:
        if f in exclude or f == path or not os.path.isfile(os.path.join(root, f)):
            continue
        try:
            with open(os.path.join(root, f), encoding="utf-8", errors="replace") as fh:
                src = fh.read()
        except OSError:
            continue
        ext = os.path.splitext(f)[1]
        if ext == ".py":
            cand, err = _py_live_strings(src)
            if err:
                cand = _line_live_lines(src, ext)
            for ln, txt in cand:
                if any(p in txt for p in pats):
                    hits.append({"pattern": [p for p in pats if p in txt][0], "file": f, "line": ln,
                                 "text": txt.strip()[:200], "kind": "py-string" + ("(unparsed)" if err else "")})
        else:
            for ln, txt in _line_live_lines(src, ext):
                if any(p in txt for p in pats):
                    hits.append({"pattern": [p for p in pats if p in txt][0], "file": f, "line": ln,
                                 "text": txt.strip()[:200], "kind": "line"})
    hits.sort(key=lambda x: (x["file"], x["line"]))
    return hits


def check(root: str, deletions: list[str]) -> dict:
    excl = set(deletions)
    per = {}
    bad = 0
    for d in deletions:
        h = refs_for(root, d, excl)
        per[d] = h
        if h:
            bad += 1
    return {"root": root, "deletions": deletions, "referenced_deletions": bad, "hits": per}


def report(res: dict) -> None:
    if not res["deletions"]:
        print("删除引用闸: 本批无删除 ⇒ PASS")
        return
    if res["referenced_deletions"] == 0:
        print("删除引用闸: %d 个删除, 0 个仍被引用 ⇒ PASS" % len(res["deletions"]))
        for d in res["deletions"]:
            print("  - %s (无引用点)" % d)
        return
    print("删除引用闸: %d/%d 个删除仍被代码/器具引用 ⇒ RED"
          % (res["referenced_deletions"], len(res["deletions"])))
    for d, h in res["hits"].items():
        if not h:
            continue
        print("  ! %s 仍被引用:" % d)
        for x in h[:12]:
            print("      %s:%s  [%s]  %s" % (x["file"], x["line"], x["pattern"], x["text"][:110]))
        if len(h) > 12:
            print("      ... 另有 %d 处" % (len(h) - 12))
    print("  处置: 要么保留该文件, 要么把引用点改成**稳定位置/候选加载器**(fail-closed), 再删。")


def _write(p: str, s: str) -> None:
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)


def selfcheck() -> int:
    """正控 = 真删除 + 真引用 ⇒ 必 rc=1 且点名; 负控 = 无引用 ⇒ 必 rc=0。
    另附**历史回放**: 对已被 R534 删除的 r504 引擎跑 --file ⇒ 当前须 PASS (证明横切修复已清干净)。"""
    import tempfile
    tmp = tempfile.mkdtemp(prefix="delref-selfcheck-")
    fails: list[str] = []

    def sh(cmd: str) -> None:
        subprocess.run(cmd, shell=True, cwd=tmp, capture_output=True, text=True, check=True)

    sh("git init -q . && git config user.email a@b.c && git config user.name t")
    _write(os.path.join(tmp, "keep.py"), "import subprocess\nsubprocess.run(['python3','gone.py'])\n")
    _write(os.path.join(tmp, "plain.py"), "print('no refs here')\n")
    _write(os.path.join(tmp, "gone.py"), "print(1)\n")
    sh("git add -A && git commit -qm init")

    # 正控: 删 gone.py, keep.py 里硬编码引用 ⇒ 必红
    os.remove(os.path.join(tmp, "gone.py"))
    sh("git add -A")
    res = check(tmp, staged_deletions(tmp))
    pc_ok = res["referenced_deletions"] == 1 and len(res["hits"].get("gone.py", [])) == 1
    print("[正控] 硬编码引用被删文件 ⇒ %s (%s)" % ("RED ✓" if pc_ok else "FAIL ✗",
                                                 json.dumps(res["hits"], ensure_ascii=False)[:160]))
    if not pc_ok:
        fails.append("正控")

    # 负控: 把引用点去掉再删 ⇒ 必绿
    _write(os.path.join(tmp, "keep.py"), "print('clean')\n")
    sh("git add -A")
    res2 = check(tmp, staged_deletions(tmp))
    nc_ok = res2["referenced_deletions"] == 0
    print("[负控] 无引用 ⇒ %s" % ("PASS ✓" if nc_ok else "FAIL ✗"))
    if not nc_ok:
        fails.append("负控")

    # 负控B: 只被 **docstring/注释** 提及 ⇒ 必绿 (叙述 ≠ 调用点; R540 首跑假红就是这个类)
    _write(os.path.join(tmp, "narr.py"), '"""引用 gone2.py 的说明文字, 不执行。"""\n# gone2.py 也不执行\nprint(1)\n')
    _write(os.path.join(tmp, "gone2.py"), "print(2)\n")
    sh("git add -A && git commit -qm add2")
    os.remove(os.path.join(tmp, "gone2.py"))
    _write(os.path.join(tmp, "narr.py"),
           '"""引用 gone2.py 的说明文字, 不执行。"""\n# gone2.py 也不执行\nprint(1)\n')
    sh("git add -A")
    res3 = check(tmp, ["gone2.py"])
    nc2_ok = res3["referenced_deletions"] == 0
    print("[负控B/叙述] 仅注释+docstring 提及 ⇒ %s" % ("PASS ✓" if nc2_ok else
                                                "FAIL ✗ " + json.dumps(res3["hits"], ensure_ascii=False)[:200]))
    if not nc2_ok:
        fails.append("负控B")

    # 历史回放 (本仓): r504 引擎 = R534 真删的真例; 横切修复后应无任何代码/器具引用
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    hr = check(root, ["eval/rover/r504/codex_solver_r504.py"])
    hr_ok = hr["referenced_deletions"] == 0
    print("[历史回放] eval/rover/r504/codex_solver_r504.py 引用点 ⇒ %s"
          % ("PASS ✓ (横切修复已清干净)" if hr_ok else "RED ✗ %s" % json.dumps(hr["hits"], ensure_ascii=False)[:200]))
    if not hr_ok:
        fails.append("历史回放")

    print("SELFCHECK %s" % ("PASS" if not fails else "FAIL " + ",".join(fails)))
    return 0 if not fails else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--staged", action="store_true")
    ap.add_argument("--file", action="append", default=[])
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    if a.selfcheck:
        return selfcheck()

    root = a.root or subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                    capture_output=True, text=True).stdout.strip()
    if not root or not os.path.isdir(root):
        print("删除引用闸: 不在 git 仓内且未给 --root ⇒ 用法错误", file=sys.stderr)
        return 3

    dels = list(a.file)
    if a.staged or not dels:
        dels += staged_deletions(root)
    dels = sorted(set(d for d in dels if d))

    res = check(root, dels)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        report(res)
    return 1 if res["referenced_deletions"] else 0


if __name__ == "__main__":
    if os.environ.get(ENV_OFF) == "0":
        print("删除引用闸: 已豁免 (%s=0)" % ENV_OFF)
        raise SystemExit(0)
    raise SystemExit(main())
