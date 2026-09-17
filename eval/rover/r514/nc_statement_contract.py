#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R514 · 题面-判据一致性机检器的**负控阶梯** (成对正/负控; 器具上线前唯一廉价闸).

结构 (每条臂都给期望判决, 期望落**机读字段** `inject_expect_rc`, 不只活在散文里):
  PC1  r513 p4 题面 v2 (修后)        期望 rc=0 无缺陷
  PC2  r512 p3 题面 (另一题族)       期望 rc=0 无缺陷
  NC1  r512 p4 题面 v1 (修前)        期望 rc=1 且 predicted binding 集合 == 归档实测失败集合 (外部锚)
  NC2  变异: v2 去掉新增句            期望 rc=1 (证明判据真的由那句决定)
  NC3  变异: 用例注入未声明选项        期望 rc=1 且 kinds 含 case_uses_option_not_in_statement
  NC4  变异: 题面删掉退出码条目        期望 rc=1 且 kinds 含 undeclared_error_token
  NC5  变异: 题面 --now 条款加可选括号  期望 rc=0 (防「恒红/恒开火」: 判据必须能被满足)
  NC6  变异: taskset 缺 cases 字段     期望 rc=2 (fail-closed, 器具缺陷, 禁计入被测读数)

纪律:
  · 变异在**临时目录的副本**上做 (冻结语料零字节改动; 收尾回读 sha 核对);
  · 前态锚 = 冻结的 r512 原文件 (禁取 `HEAD`, HEAD 会前进而静默失效);
  · 期望值从**归档实测**取 (禁手抄): 外部锚由 `--rebuild-anchor` 从 R512 run 产物派生并登记来源 sha。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CHECKER = os.path.join(HERE, "statement_contract_check.py")
FIX = os.path.join(HERE, "fixtures")
ANCHOR = os.path.join(FIX, "r512-p4-observed-failing.json")
TS512 = os.path.join(HERE, "..", "r512", "taskset-r512.json")
TS513 = os.path.join(HERE, "..", "r513", "taskset-r513.json")
CASES512 = os.path.join(HERE, "..", "r512", "cases", "p4_cases.py")
CASES513 = os.path.join(HERE, "..", "r513", "cases", "p4_cases.py")
R512_REPORT = "/tmp/r512/run-0917-095853/report.json"


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def rebuild_anchor():
    """从 R512 run 产物派生外部锚 (机取, 禁手抄)。"""
    if not os.path.isfile(R512_REPORT):
        print("[器具缺陷 rc=2] 缺 R512 run 产物 %s ⇒ 无法派生外部锚 (fail-closed, 禁手抄)" % R512_REPORT)
        return 2
    rep = json.load(open(R512_REPORT, encoding="utf-8-sig"))
    rows = [r for r in rep["rows"] if r.get("tid") == "p4"]
    if not rows:
        print("[器具缺陷 rc=2] R512 产物里没有 p4 行")
        return 2
    counts = {}
    for r in rows:
        counts.setdefault(tuple(sorted(r.get("failed") or [])), []).append(r.get("run") or r.get("arm"))
    modal, runs = max(counts.items(), key=lambda kv: len(kv[1]))
    doc = {"source": R512_REPORT, "source_sha256": sha(R512_REPORT),
           "taskset": os.path.relpath(TS512, REPO), "taskset_sha256": sha(TS512),
           "derived_by": "eval/rover/r514/nc_statement_contract.py --rebuild-anchor",
           "p4": {"observed_failing_modal": list(modal), "modal_runs": sorted(runs),
                  "all_runs": {str(r.get("run")): sorted(r.get("failed") or []) for r in rows},
                  "note": "众数 = 6 跑次里 5 次完全相同的失败集合; A-r1 为 10 条的另一失效形态(单列)"}}
    os.makedirs(FIX, exist_ok=True)
    with open(ANCHOR, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps({"anchor": ANCHOR, "modal": list(modal), "runs": sorted(runs)}, ensure_ascii=False))
    return 0


def check_json_tid(taskset, tid):
    return check_json(taskset, "tid:%s" % tid, tid=tid)


def run_checker(taskset, extra=()):
    p = subprocess.run([sys.executable, CHECKER, "--taskset", taskset] + list(extra),
                       capture_output=True, text=True)
    out = {"rc": p.returncode, "stdout": p.stdout}
    try:
        out["json"] = json.loads(p.stdout.split("### JSON ###")[-1]) if "### JSON ###" in p.stdout else None
    except Exception:  # noqa: BLE001
        out["json"] = None
    return out


def check_json(taskset, tag, tid=None):
    """带 --json 的调用, 拿机读判决 (期望值只认机读字段)。"""
    with tempfile.TemporaryDirectory(prefix="r514nc-") as d:
        jp = os.path.join(d, "out.json")
        cmd = [sys.executable, CHECKER, "--taskset", taskset, "--json", jp]
        if tid:
            cmd += ["--tid", tid]
        p = subprocess.run(cmd, capture_output=True, text=True)
        doc = json.load(open(jp, encoding="utf-8")) if os.path.isfile(jp) else None
        return {"rc": p.returncode, "doc": doc if isinstance(doc, dict) else {}, "stdout": p.stdout, "tag": tag}


def _mutant_dir(base_ts, base_cases):
    """副本目录保持题集声明的相对布局 (cases 字段是相对路径 ⇒ 布局必须同构)。"""
    d = tempfile.mkdtemp(prefix="r514mut-")
    ts = json.load(open(base_ts, encoding="utf-8-sig"))
    rels = {t["cases"] for t in ts["tasks"] if t.get("cases")}
    for rel in rels:
        dst = os.path.join(d, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(base_cases if rel.endswith(os.path.basename(base_cases))
                    else os.path.join(os.path.dirname(base_cases), os.path.basename(rel)), dst)
    ts_path = os.path.join(d, "taskset.json")
    return d, ts, ts_path


def write_ts(d, ts, ts_path):
    with open(ts_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(ts, ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild-anchor", action="store_true")
    ap.add_argument("--json", default=os.path.join(HERE, "evidence", "nc-r514.json"))
    a = ap.parse_args()
    if a.rebuild_anchor:
        return rebuild_anchor()
    if not os.path.isfile(ANCHOR):
        print("[器具缺陷 rc=2] 缺外部锚 %s ⇒ 先 --rebuild-anchor (fail-closed)" % ANCHOR)
        return 2
    anchor = json.load(open(ANCHOR, encoding="utf-8-sig"))
    if sha(TS512) != anchor["taskset_sha256"]:
        print("[器具缺陷 rc=2] 冻结题集 sha 与锚登记不符 ⇒ 语料已变, 锚不可用 (fail-closed)")
        return 2
    frozen_before = {p: sha(p) for p in (TS512, TS513, CASES512, CASES513)}
    observed = sorted(anchor["p4"]["observed_failing_modal"])
    arms, fails = [], []
    tmp_dirs = []

    def record(tag, expect_rc, expect_kinds=(), expect_binding=None, got=None, note=""):
        ok = got["rc"] == expect_rc
        detail = {"tag": tag, "inject_expect_rc": expect_rc, "rc": got["rc"], "ok": ok, "note": note,
                  "stdout_head": got["stdout"][:300]}
        if expect_kinds:
            kinds = sorted({k for t in (got["doc"] or {}).get("tasks", []) for k in t["defect_kinds"]})
            detail["kinds"] = kinds
            detail["kinds_ok"] = all(k in kinds for k in expect_kinds)
            ok = ok and detail["kinds_ok"]
        if expect_binding is not None:
            got_b = sorted({c for t in (got["doc"] or {}).get("tasks", [])
                            for c in t["predicted_binding_failures"]})
            detail["predicted_binding"] = got_b
            detail["binding_eq_observed"] = got_b == expect_binding
            detail["binding_expect"] = expect_binding
            ok = ok and detail["binding_eq_observed"]
        detail["ok"] = ok
        arms.append(detail)
        if not ok:
            fails.append(tag)

    # PC1 / PC2 / NC1
    g = check_json(TS513, "PC1"); record("PC1_r513_v2_no_defect", 0, (), got=g)
    g = check_json_tid(TS512, "p3"); record("PC2_r512_p3_no_defect", 0, (), got=g, note="定向 --tid p3")
    g = check_json(TS512, "NC1"); record("NC1_r512_p4_v1_defect_vs_anchor", 1,
                                         ("reliance_on_unstated_default",), observed, got=g,
                                         note="binding 集合 == 归档实测失败集合(众数)")

    # NC2: v2 去掉新增句
    d, ts, tsp = _mutant_dir(TS513, CASES513); tmp_dirs.append(d)
    ts["tasks"][0]["prompt"] = ts["tasks"][0]["prompt"].replace(
        "**未提供 `--now` 时必须回落到系统时钟（time.time()），不得报错、不得要求该选项必填。**", "")
    write_ts(d, ts, tsp)
    g = check_json(tsp, "NC2"); record("NC2_v2_minus_added_clause", 1, ("reliance_on_unstated_default",), got=g)

    # NC3: 用例注入未声明选项
    d, ts, tsp = _mutant_dir(TS513, CASES513); tmp_dirs.append(d)
    cpath = os.path.join(d, ts["tasks"][0]["cases"])
    src = open(cpath, encoding="utf-8").read()
    src = src.replace('rc, out, err = cli("--db", db, "add", "买菜")',
                      'rc, out, err = cli("--db", db, "--verbose", "add", "买菜")', 1)
    open(cpath, "w", encoding="utf-8", newline="\n").write(src)
    write_ts(d, ts, tsp)
    g = check_json(tsp, "NC3"); record("NC3_case_uses_undeclared_option", 1,
                                       ("case_uses_option_not_in_statement",), got=g)

    # NC4: 题面删掉退出码条目
    d, ts, tsp = _mutant_dir(TS513, CASES513); tmp_dirs.append(d)
    p = ts["tasks"][0]["prompt"]
    cut = [s for s in p.split("\n") if s.startswith("8) 退出码")]
    if not cut:
        print("[器具缺陷 rc=2] 变异前置条件不满足: 题面里找不到退出码条目 ⇒ fail-closed")
        return 2
    ts["tasks"][0]["prompt"] = p.replace(cut[0], "8) 退出码：按常规。")
    write_ts(d, ts, tsp)
    g = check_json(tsp, "NC4"); record("NC4_exit_code_clause_removed", 1, ("undeclared_error_token",), got=g)

    # NC5: 题面 --now 条款加可选括号 ⇒ 判据必须能被满足 (防恒红)
    d, ts, tsp = _mutant_dir(TS512, CASES512); tmp_dirs.append(d)
    p = ts["tasks"][1]["prompt"]
    old = "2) 时钟：全局选项 `--now <epoch 秒>` 注入当前时间（浮点或整数）。"
    if old not in p:
        print("[器具缺陷 rc=2] 变异前置条件不满足: 找不到 --now 条款 ⇒ fail-closed")
        return 2
    ts["tasks"][1]["prompt"] = p.replace(old, "2) 时钟：[全局选项 `--now <epoch 秒>` 注入当前时间（浮点或整数）]。")
    write_ts(d, ts, tsp)
    g = check_json(tsp, "NC5"); record("NC5_optional_bracket_suppresses_flag", 0, (), got=g,
                                       note="只判 rc + 无 D2; 该臂证明判据非恒开火")

    # NC6: 缺 cases 字段 ⇒ fail-closed rc=2
    d, ts, tsp = _mutant_dir(TS513, CASES513); tmp_dirs.append(d)
    ts["tasks"][0].pop("cases", None)
    write_ts(d, ts, tsp)
    g = check_json(tsp, "NC6"); record("NC6_missing_cases_field_fail_closed", 2, (), got=g)

    # 收尾: 冻结语料零字节改动
    frozen_after = {p: sha(p) for p in (TS512, TS513, CASES512, CASES513)}
    frozen_ok = frozen_before == frozen_after
    for d in tmp_dirs:
        shutil.rmtree(d, ignore_errors=True)
    doc = {"anchor": os.path.relpath(ANCHOR, REPO), "anchor_source": anchor["source"],
           "anchor_source_sha256": anchor["source_sha256"],
           "observed_failing_set": observed, "arms": arms,
           "frozen_fixtures_unchanged": frozen_ok,
           "frozen_shas": frozen_after,
           "verdict": "OK" if (not fails and frozen_ok) else "FAIL",
           "failed_arms": fails}
    os.makedirs(os.path.dirname(a.json), exist_ok=True)
    with open(a.json, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False, indent=1))
    for arm in arms:
        print("%-46s expect_rc=%d rc=%d %s" % (arm["tag"], arm["inject_expect_rc"], arm["rc"],
                                               "OK" if arm["ok"] else "FAIL"))
    print("frozen_fixtures_unchanged=%s verdict=%s failed=%s" % (frozen_ok, doc["verdict"], fails or "-"))
    return 0 if doc["verdict"] == "OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
