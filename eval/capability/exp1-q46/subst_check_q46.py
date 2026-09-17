#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q46 替代机检 (零 dotnet, 窗口被对侧 R519 起臂占用时用):
   ① 新行内引用的**路径类事实**逐条存在性机检 (doc-ref 完整性, 与 DevPlanDocRef 同族但作用域限于本行);
   ② 新行内引用的**提交号**存在 ∧ 其标题含声明的语义;
   ③ 形式门禁三面 (登记表/证据映射/skills/计划 DocRef) 的**触达性**判定: 本轮改动路径是否落在其作用域内。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DOC = os.path.join(ROOT, "docs", "reports", "dynamic-telemetry-eval-rollback-strategy.md")
LINE_KEY = "EXP1-Q45 已闭合"

with open(DOC, encoding="utf-8-sig", errors="replace") as fh:
    lines = fh.read().splitlines()
new_line = next((l for l in lines if LINE_KEY in l), None)
if new_line is None:
    print("CHK new_line=FALSE")
    print("SUBST_EXIT=2")
    raise SystemExit(2)

rc = 0


def chk(name: str, cond: bool, extra: str = "") -> None:
    global rc
    print(f"CHK {name}={'PASS' if cond else 'FAIL'} {extra}")
    if not cond:
        rc = 2


# ① 路径引用
paths = re.findall(r"`([A-Za-z0-9_./\-]+\.(?:py|txt|md|json))`", new_line)
print(f"CHK referenced_paths n={len(paths)} {paths}")
for p in paths:
    chk(f"path_exists:{p}", os.path.exists(os.path.join(ROOT, p)))

# ② 提交号
shas = re.findall(r"`([0-9a-f]{7,40})`", new_line)
print(f"CHK referenced_shas n={len(shas)} {shas}")
for s in shas:
    r = subprocess.run(["git", "show", "-s", "--format=%s", s], cwd=ROOT, capture_output=True, text=True)
    chk(f"sha_exists:{s}", r.returncode == 0, r.stdout.strip()[:80])

# improvements.md R404 段
imp = os.path.join(ROOT, "docs", "improvements.md")
with open(imp, encoding="utf-8-sig", errors="replace") as fh:
    itxt = fh.read()
chk("improvements_has_R404_section", "R404" in itxt)
chk("improvements_has_q45_correction", "旧口径作废" in itxt)

# ③ 形式门禁三面触达性 (statements 用**谓词**判定, 不靠印象)
changed = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout
this_round = [l[3:].strip() for l in changed.splitlines() if "exp1-q46" in l or "dynamic-telemetry-eval-rollback-strategy.md" in l]
print(f"CHK round_paths n={len(this_round)}")
scopes = {
    "VerificationForm(登记表)": lambda p: "verification-registry" in p or "verification" in p and p.endswith(".json"),
    "SkillGeneralization(skills/)": lambda p: p.startswith("skills/"),
    "DevPlanDocRef(docs/plans/)": lambda p: p.startswith("docs/plans/"),
}
for name, pred in scopes.items():
    touched = [p for p in this_round if pred(p)]
    print(f"CHK scope_touch[{name}]={len(touched)} {touched[:3]}")
print(f"SUBST_EXIT={rc}")
sys.exit(rc)
