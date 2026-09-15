#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R481-D9 器具: 交替核验 (目录 mtime 剪枝对「纯内容改写」不可见) 的源码派生判据 + 真读数 + 变异负控。

判据面 (全 fail-closed: 取不到即红, 不写 "大概是" )
  C1 源码派生 · 读写契约成对:
     - 读侧 stamp 解码 `(ticks >> 1)` 与标志位 `(ticks & 1UL) != 0UL` 必须同时存在
     - 剪枝开关必须由 `pruneEnabled` 表达, 且其定义里含 `!prevScanPruned` (上轮剪过 ⇒ 本轮抑制剪枝)
     - 写侧 stamp 编码必须为 `(base << 1) | (本轮剪枝 ? 1 : 0)`
     - `BackfillHeader` 的 stamp 形参必须是 `ulong` (编码后的值, 不得在回填处再截断)
  C2 真读数 · 测试面: 真跑 `agent.recall.tests`, 断言 Failed==0 ∧ Total>=14 ∧ D9 回归用例存在且 Passed ∧
     **断言执行数 > 0** (以该用例产生的 trx 结果数为代理; 禁假绿)
  C3 语义计数: 「核验轮 DirsPruned 恒 0」必须有断言锁存 (源码派生), 否则语义只是注释
负控 (变异测试: 判据必须对**注入缺陷**翻红, 否则判据恒绿 = 无效)
  NC1 把 `!prevScanPruned` 反转 ⇒ 判红
  NC2 删掉 stamp 低位编码 (`<< 1`) ⇒ 判红
  NC3 删掉读侧标志位解码 ⇒ 判红
用法: python3 eval/recall/r481/check_r481d9.py [--source <RecallFingerprint.cs>] [--no-test]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

BASE = "/home/agentuser/AgentFramework"
SRC = os.path.join(BASE, "src/agent.recall/RecallFingerprint.cs")
TESTS_SRC = os.path.join(BASE, "src/agent.recall.tests/RecallModuleTests.cs")
OUT_DIR = os.path.join(BASE, "eval/recall/r481")
TRX_DIR = os.path.join(OUT_DIR, "results")
DOTNET = os.path.expanduser("~/.dotnet/dotnet")
D9_TEST = "Update_AlternatingVerify_CatchesSameSizeContentRewrite"

_ap = argparse.ArgumentParser()
_ap.add_argument("--source", default=SRC, help="被测源码 (变异负控用临时副本)")
_ap.add_argument("--no-test", action="store_true", help="只跑源码派生判据 (不真跑测试)")
args = _ap.parse_args()

checks, negs = {}, {}


def record(d, k, ok, detail):
    d[k] = {"ok": bool(ok), "detail": detail}


def read(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return f.read()


def code_of(path):
    """剥掉注释与空行后的源码面 (判据只认代码, 不认注释里的字面量)。"""
    text = read(path)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    return text


# ---------- C1 源码派生 (可对任意注入副本求值 ⇒ 支撑变异负控) ----------
def c1_eval(path):
    code = code_of(path)
    detail = {}
    detail["read_shift"] = bool(re.search(r"lastScanTicks\s*=\s*\(long\)\(ticks\s*>>\s*1\)", code))
    detail["read_flag"] = bool(re.search(r"prevScanPruned\s*=\s*\(ticks\s*&\s*1UL\)\s*!=\s*0UL", code))
    m = re.search(r"bool\s+pruneEnabled\s*=\s*([^;]+);", code)
    detail["prune_enabled_decl"] = m.group(1).strip() if m else None
    detail["prune_gate_suppresses"] = bool(m and "!prevScanPruned" in m.group(1))
    detail["write_encode"] = bool(
        re.search(r"\(\(ulong\)stampBase\s*<<\s*1\)\s*\|\s*\(result\.DirsPruned\s*>\s*0\s*\?\s*1UL\s*:\s*0UL\)", code)
    )
    detail["backfill_ulong"] = bool(re.search(r"BackfillHeader\([^)]*ulong\s+stamp[^)]*\)", code))
    ok = all(bool(v) for k, v in detail.items() if k != "prune_enabled_decl")
    return ok, detail


ok1, d1 = c1_eval(args.source)
record(checks, "C1_source_derived_contract", ok1, d1)

# ---------- C3 语义计数锁存 (源码派生) ----------
tcode = code_of(TESTS_SRC)
c3 = {
    "d9_test_present": D9_TEST in tcode,
    "asserts_zero_prune_on_verify_round": bool(re.search(r"Assert\.Equal\(0,\s*\w+\.DirsPruned\)", tcode)),
    "asserts_verify_flag": bool(re.search(r"Assert\.True\(\w+\.VerifiedAllDirs\)", tcode)),
    "asserts_alternation_recovers": bool(re.search(r"Assert\.True\(\w+\.DirsPruned\s*>=\s*1\)", tcode)),
}
record(checks, "C3_verify_round_semantics_locked", all(c3.values()), c3)

# ---------- C2 真读数 (真跑测试工程) ----------
c2 = {"ran": False}
if not args.no_test:
    os.makedirs(TRX_DIR, exist_ok=True)
    cmd = [
        DOTNET, "test", "src/agent.recall.tests/agent.recall.tests.csproj", "-c", "Release",
        "--nologo", "-v", "q", "--logger", "trx;LogFileName=r481d9.trx",
        "--results-directory", TRX_DIR,
    ]
    env = dict(os.environ)
    env["DOTNET_ROOT"] = os.path.expanduser("~/.dotnet")
    env.pop("AGENTFRAMEWORK_PY_RUN", None)
    env.pop("AGENTFRAMEWORK_ARTIFACT_REPAIR", None)
    p = subprocess.run(cmd, cwd=BASE, env=env, capture_output=True, text=True, timeout=1800)
    c2["rc"] = p.returncode
    c2["ran"] = True
    c2["tail"] = (p.stdout or "")[-400:]
    trx = os.path.join(TRX_DIR, "r481d9.trx")
    if os.path.exists(trx):
        root = ET.parse(trx).getroot()
        ns = {"t": "http://microsoft.com/schemas/VisualStudio/TeamTest/2010"}
        results = root.findall(".//t:UnitTestResult", ns)
        c2["result_rows"] = len(results)
        c2["failed"] = sum(1 for r in results if r.get("outcome") == "Failed")
        c2["passed"] = sum(1 for r in results if r.get("outcome") == "Passed")
        names = [r.get("testName") or "" for r in results]
        c2["d9_case"] = [n for n in names if D9_TEST in n]
        c2["d9_passed"] = any(D9_TEST in n and r.get("outcome") == "Passed"
                              for n, r in zip(names, results))
    else:
        c2["trx"] = "missing"
ok2 = bool(c2.get("rc") == 0 and c2.get("failed") == 0 and (c2.get("result_rows") or 0) > 0
           and (c2.get("passed") or 0) >= 14 and c2.get("d9_case") and c2.get("d9_passed"))
record(checks, "C2_real_test_readout", ok2, c2)

# ---------- 负控: 变异测试 (判据必须对注入缺陷翻红) ----------
src_text = read(SRC)
mutants = {
    "NC1_invert_prune_gate": src_text.replace("&& !prevScanPruned", "&& prevScanPruned", 1),
    "NC2_drop_stamp_shift": src_text.replace("((ulong)stampBase << 1) |", "((ulong)stampBase) |", 1),
    "NC3_drop_flag_decode": src_text.replace("prevScanPruned = (ticks & 1UL) != 0UL;", "prevScanPruned = false;", 1),
}
tmp_path = os.path.join(OUT_DIR, "_mutant.cs")
for name, text in mutants.items():
    if text == src_text:
        record(negs, name, False, "mutation target not found (源码面漂移 ⇒ 负控失效, 判红)")
        continue
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(text)
    ok_mut, detail_mut = c1_eval(tmp_path)
    record(negs, name, not ok_mut, {"detector_ok_on_mutant": ok_mut})
if os.path.exists(tmp_path):
    os.remove(tmp_path)

all_ok = all(v["ok"] for v in checks.values()) and all(v["ok"] for v in negs.values())
verdict = {
    "round": "R481",
    "subject": "D9 交替核验 (目录 mtime 剪枝盲区: 纯内容改写)",
    "checks": checks,
    "negative_controls": negs,
    "verdict": "PASS" if all_ok else "FAIL",
    "note": "C2 为真跑读数 (trx 结果行数 = 断言执行面代理, 0 行 ⇒ 假绿判红); 变异负控在**临时副本**上求值, 不动工作树源码。",
}
if not args.no_test:
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "verdict-r481d9.json"), "w", encoding="utf-8") as f:
        json.dump(verdict, f, ensure_ascii=False, indent=1)
print(json.dumps(verdict, ensure_ascii=False, indent=1)[:2200])
sys.exit(0 if all_ok else 1)
