#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q44 · C2 器具: 「rc 假绿」fail-closed 检测器 (两个独立面, 各自可证).

背景 (真机证据, 本轮取证): `/tmp/r508_fulltest.log` 尾部同时出现
    `Failed!  - Failed:     1, Passed:  1635, ...`  与
    `TEST_RC=0`
⇒ 记录侧 rc 与日志正文**互相矛盾**: rc 取自**管道末段** (tail/head/grep) 而非被测命令。

判据设计 (rc 语义分层: 0 过 / 1 被测不满足 / 2 器具缺陷 / 3 缺侧):
  A 日志面 `--check-log`: 记录 rc 标记与日志正文的**矛盾检测** —— 正文报 Failed>0 而 rc 标记=0 ⇒ 1 (假绿);
     正文无任何判定行 ⇒ 2 (器具缺陷: 采集侧无结论, 不得当通过); rc 标记缺失 ⇒ 2。
  B 脚本面 `--scan-scripts`: 扫描 shell 脚本里「rc 取自管道末段」的形态 ⇒ 1 (器具缺陷, 但归类为被测=脚本)。
  C 通用面 `--check-rc`: 纯 rc 语义: `rc == 0` 且本文件声明「必须显式标记」时, 无标记即 2。

负控 (判别力自证, 两侧都动):
  N1 构造**好日志**(Passed! + 标记 0) ⇒ A 必须放行 (0)  —— 防「凡有 rc 标记就判红」的空心判据
  N2 构造**坏日志**(Failed: 1 + 标记 0) ⇒ A 必须判 1      —— 证明 A 有判别力
  N3 构造**无判定行日志** ⇒ A 必须判 2 (不是 0, 不是 1)   —— 「没测到」≠「测过通过」
  N4 好脚本 (显式记录 rc 于管道**之前**) ⇒ B 必须 0
  N5 坏脚本 (`RC=$(cmd | tail -3)`)      ⇒ B 必须 1      —— 证明 B 有判别力
"""
from __future__ import annotations

import argparse
import os
import re
import sys

# 记录侧 rc 标记 (由发射点显式书写; 名称不限, 语义 = 「被测命令的退出码」)
RC_MARK = re.compile(r"^\s*(?:[A-Z0-9_]*?(?:RC|EXIT))\s*=\s*(-?\d+)\s*$")
FAIL_LINE = re.compile(r"Failed!\s+-\s+Failed:\s+(\d+),\s+Passed:\s+(\d+)")
PASS_LINE = re.compile(r"Passed!\s+-\s+Failed:\s+(\d+),\s+Passed:\s+(\d+)")
# 脚本面: rc/exit 变量取值自**管道末段** (tail/head/grep/tee 之后的 $? 也算)
PIPE_TAIL_RC = re.compile(r"\$\s*\([^()]*\|\s*(?:tail|head|grep|tee|sed|awk)\b[^()]*\)")
RC_ASSIGN = re.compile(r"^\s*(?:[A-Za-z0-9_]*?(?:RC|EXIT|exit_code))\s*=\s*(.+)$")


def lines_of(path: str) -> list[str]:
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read().splitlines()


def check_log(path: str) -> tuple[int, dict]:
    if not os.path.exists(path):
        return 3, {"why": "log_missing", "path": path}
    ls = lines_of(path)
    marks = [(i + 1, int(m.group(1))) for i, l in enumerate(ls) for m in [RC_MARK.match(l)] if m]
    failed = [(i + 1, int(m.group(1)), int(m.group(2))) for i, l in enumerate(ls)
              for m in [FAIL_LINE.match(l.strip())] if m]
    passed = [(i + 1, int(m.group(1)), int(m.group(2))) for i, l in enumerate(ls)
              for m in [PASS_LINE.match(l.strip())] if m]
    diag = {"rc_marks": marks, "fail_lines": failed, "pass_lines": passed,
            "log_lines": len(ls)}
    if not marks:
        # 采集侧没有结论 = 器具缺陷 (不是「通过」); 与「缺字段记 n/a 不记 0」同族
        return 2, dict(diag, why="no_rc_marker (采集侧无结论 ⇒ fail-closed 为器具缺陷)")
    rc = marks[-1][1]
    verdict_lines = failed or passed
    if not verdict_lines:
        return 2, dict(diag, why="no_verdict_line (日志内无 Passed!/Failed! 判定行 ⇒ 不得当通过)")
    f_cnt = failed[-1][1] if failed else passed[-1][1]
    if f_cnt > 0 and rc == 0:
        return 1, dict(diag, why=f"FALSE_GREEN: 正文 Failed={f_cnt} 而 rc 标记=0 "
                                 f"(rc 疑取自管道末段; 标记行={marks[-1][0]})")
    if f_cnt == 0 and rc != 0:
        return 1, dict(diag, why=f"FALSE_RED: 正文 Failed=0 而 rc 标记={rc}")
    return 0, dict(diag, why="consistent")


def scan_scripts(root: str) -> tuple[int, dict]:
    if not os.path.isdir(root):
        return 3, {"why": "root_missing", "root": root}
    hits, scanned = [], 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in {".git", "__pycache__", "node_modules", "bin", "obj"}]
        for fn in filenames:
            if not fn.endswith(".sh"):
                continue
            p = os.path.join(dirpath, fn)
            scanned += 1
            try:
                ls = lines_of(p)
            except OSError as exc:                       # IO 异常留告警, 不静默
                hits.append({"file": p, "line": 0, "why": f"io_warning: {exc}"})
                continue
            for i, l in enumerate(ls):
                m = RC_ASSIGN.match(l)
                if m and PIPE_TAIL_RC.search(m.group(1)):
                    hits.append({"file": os.path.relpath(p, root), "line": i + 1,
                                 "why": "rc 取值自管道末段 (tail/head/grep)",
                                 "text": l.strip()[:120]})
    diag = {"scripts_scanned": scanned, "hits": hits}
    return (1 if hits else 0), diag


FIXTURE_GOOD_LOG = """Determining projects to restore...
Passed!  - Failed:     0, Passed:  1636, Skipped:     0, Total:  1636, Duration: 41 s
TEST_RC=0
"""
FIXTURE_BAD_LOG = """Failed!  - Failed:     1, Passed:  1635, Skipped:     0, Total:  1636, Duration: 41 s
TEST_RC=0
"""
FIXTURE_NOVERDICT_LOG = """Determining projects to restore...
Restored /x/y.csproj (in 1.2 sec).
TEST_RC=0
"""
FIXTURE_GOOD_SH = """#!/bin/bash
set -euo pipefail
dotnet test x.csproj --nologo -v q > full.log 2>&1
TEST_RC=$?
echo "TEST_RC=$TEST_RC" >> full.log
tail -3 full.log
"""
FIXTURE_BAD_SH = """#!/bin/bash
TEST_RC=$(dotnet test x.csproj --nologo -v q 2>&1 | tail -3)
echo "TEST_RC=$TEST_RC"
"""


def selftest() -> int:
    import tempfile
    tmp = tempfile.mkdtemp(prefix="pipeline-rc-selftest-")
    fails, checks = 0, []

    def w(name, text):
        p = os.path.join(tmp, name)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        return p

    def chk(name, cond, got):
        nonlocal fails
        checks.append((name, bool(cond), got))
        if not cond:
            fails += 1

    # 正面 + 负控 (成对): 每一侧都必须给出预期读数, 否则「怎么改都红/都绿」
    rc_g, d_g = check_log(w("good.log", FIXTURE_GOOD_LOG))
    rc_b, d_b = check_log(w("bad.log", FIXTURE_BAD_LOG))
    rc_n, d_n = check_log(w("noverdict.log", FIXTURE_NOVERDICT_LOG))
    rc_m, d_m = check_log(os.path.join(tmp, "absent.log"))
    chk("T1 好日志 ⇒ 放行 (0)", rc_g == 0, (rc_g, d_g["why"]))
    chk("T2 坏日志 (Failed:1 而 rc=0) ⇒ 假绿 (1)", rc_b == 1, (rc_b, d_b["why"]))
    chk("T3 无判定行 ⇒ 器具缺陷 (2), 不当通过也不当被测红", rc_n == 2, (rc_n, d_n["why"]))
    chk("T4 日志缺失 ⇒ 缺侧 (3)", rc_m == 3, (rc_m, d_m["why"]))
    # N1/N2/N3 = 判别力负控 (与 T1/T2/T3 成对: 同样的检测器必须给出**不同**读数)
    chk("N1 判别力: 好/坏日志读数互异 (0 vs 1)", rc_g != rc_b, (rc_g, rc_b))
    chk("N2 判别力: 无判定行 ≠ 好日志 (2 vs 0)", rc_n != rc_g, (rc_n, rc_g))
    d = os.path.join(tmp, "scripts")
    os.makedirs(d, exist_ok=True)
    w(os.path.join("scripts", "good.sh"), FIXTURE_GOOD_SH)
    w(os.path.join("scripts", "bad.sh"), FIXTURE_BAD_SH)
    rc_s, d_s = scan_scripts(d)
    chk("T5 坏脚本 (rc 取自管道末段) 被检出 ⇒ 1", rc_s == 1, d_s)
    chk("T6 好脚本不被误报", all("good.sh" not in h["file"] for h in d_s["hits"]), d_s["hits"])
    chk("N3 脚本面两侧读数互异 (有判别力)", rc_s == 1 and len(d_s["hits"]) == 1, d_s)
    for name, ok, got in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}  got={got}")
    print(f"selftest: {len(checks) - fails}/{len(checks)} passed")
    return 0 if fails == 0 else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="rc 假绿 fail-closed 检测器")
    ap.add_argument("--check-log")
    ap.add_argument("--scan-scripts")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    rc_out = 0
    if a.check_log:
        rc, d = check_log(a.check_log)
        print(f"[log] rc={rc} {d}")
        rc_out = max(rc_out, rc)
    if a.scan_scripts:
        rc, d = scan_scripts(a.scan_scripts)
        print(f"[scripts] rc={rc} scanned={d['scripts_scanned']} hits={len(d['hits'])}")
        for h in d["hits"]:
            print(f"   {h['file']}:{h['line']}  {h['why']}  | {h.get('text','')}")
        rc_out = max(rc_out, rc)
    return rc_out


if __name__ == "__main__":
    sys.exit(main())
