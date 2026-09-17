#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R512 预注册器 (机检, fail-closed): 起臂**之前**冻结 题面/器具/判据/验收面 的哈希与阈值。

为什么: 判据纪律 —— 预注册被证伪 ⇒ 宣称收窄 + 事后项单列; 事后补记一律不得当验收依据。
本器只做两件事: (1) 逐文件 sha256 + 题面 sha; (2) 写 criteria/evidence_scope (机检项写成可执行口径)。
校验: `--check` 时逐项与现盘比对, 任一漂移 ⇒ rc=3。
"""
from __future__ import annotations
import argparse, hashlib, io, json, os, subprocess, sys

REPO = "/home/agentuser/AgentFramework"
HERE = os.path.join(REPO, "eval/rover/r512")

INSTRUMENTS = {
    "taskset": "eval/rover/r512/taskset-r512.json",
    "cases_p3": "eval/rover/r508/cases/p3_cases.py",
    "cases_p4": "eval/rover/r511/cases/p4_cases.py",
    "runner_side": "eval/rover/r511/proj_run_side.py",
    "grade": "eval/rover/r511/grade_r511.py",
    "usage": "eval/rover/r511/usage_from_dumps.py",
    "aggregate": "eval/rover/r512/aggregate_r512.py",
    "freeze": "eval/rover/r512/freeze_snapshot_r512.py",
    "taskset_builder": "eval/rover/r512/build_taskset_r512.py",
    "precondition": "eval/rover/r507pre/exec_precondition.py",
    "codex_engine": "eval/rover/r504/codex_solver_r504.py",
    "preflight_gate": "eval/rover/r483/preflight_gate.py",
    "runner_contrast": "eval/rover/r512/run_contrast_r512.sh",
}

CRITERIA = {
    "C1_same_env_same_input_same_model": {
        "rule": "两侧读同一 taskset-r512.json (题面 sha 逐题相等); adapter 落盘 models 集合两侧相等且非空",
        "machine_check": "argv.model_agreement_and_prompt_sha",
    },
    "C2_quality_not_lower": {
        "rule": "每窗口 本侧 agentA 整题全对 2/2 且用例全过; 用例通过率 >= codex 侧",
        "machine_check": "argv.cases_pass_ratio",
    },
    "C3_token_down": {
        "rule": "每窗口 本侧 total_tokens <= 0.70 * codex total_tokens (上游 usage 真值; unreported 单列)",
        "machine_check": "argv.total_tokens_ratio",
    },
    "C4_remote_calls_down": {
        "rule": "每窗口 本侧 calls <= codex calls (adapter 去重请求数)",
        "machine_check": "argv.calls_ratio",
    },
    "C5_executable_and_correct": {
        "rule": "铁律11: exec_precondition --round R512 rc=0 (仓内快照独立物化跑隐藏用例, 自报只作对照)",
        "machine_check": "exec_precondition_rc",
    },
}


def sha(p):
    h = hashlib.sha256()
    with io.open(os.path.join(REPO, p), "rb") as fh:
        for b in iter(lambda: fh.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


def tree_sha(rel_dir):
    """目录指纹: 逐文件 (相对路径, sha256) 排序后合并哈希。"""
    root = os.path.join(REPO, rel_dir)
    items = []
    for r, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in sorted(files):
            fp = os.path.join(r, f)
            items.append((os.path.relpath(fp, root), sha(os.path.relpath(fp, REPO))))
    items.sort()
    h = hashlib.sha256()
    for name, s in items:
        h.update(("%s %s\n" % (name, s)).encode("utf-8"))
    return h.hexdigest(), len(items)


def build():
    doc = {"round": "R512", "written_by": "eval/rover/r512/make_prereg_r512.py",
           "head_sha": subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"],
                                      capture_output=True, text=True).stdout.strip(),
           "instruments": {}, "criteria": CRITERIA,
           "evidence_scope": {"require": ["*/agentA", "*/codex"],
                              "nonrequired": [],
                              "note": "两侧皆为验收面; 任一臂-题不可执行/不通过 ⇒ 本轮 token 降幅标『参考(未可验收)』"},
           "exploratory_not_preregistered": [
               "『口述不落盘』(调用数=0 且回复含代码块) 的机制定位与样本率 —— 事后探索, 不得当验收依据"]}
    for k, p in INSTRUMENTS.items():
        fp = os.path.join(REPO, p)
        doc["instruments"][k] = {"path": p, "sha256": sha(p) if os.path.isfile(fp) else None,
                                 "exists": os.path.isfile(fp)}
    doc["instruments"]["ref_p3"] = {"path": "eval/rover/r508/ref/p3"} | dict(zip(("sha256", "files"), tree_sha("eval/rover/r508/ref/p3")))
    doc["instruments"]["ref_p4"] = {"path": "eval/rover/r511/ref/p4"} | dict(zip(("sha256", "files"), tree_sha("eval/rover/r511/ref/p4")))
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", default=os.path.join(HERE, "prereg-r512.json"))
    a = ap.parse_args()
    doc = build()
    missing = [k for k, v in doc["instruments"].items() if not v.get("exists", True)]
    if missing:
        print("[致命] 器具缺失: %s ⇒ FAIL-CLOSED" % missing)
        return 3
    if a.write:
        ts = json.load(io.open(os.path.join(REPO, "eval/rover/r512/taskset-r512.json"), encoding="utf-8-sig"))
        doc["prompt_sha256"] = {t["tid"]: t["prompt_sha256"] for t in ts["tasks"]}
        with io.open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
        print("WROTE %s %d 项器具 · %d 判据 · 验收面 %s" %
              (a.out, len(doc["instruments"]), len(CRITERIA), doc["evidence_scope"]["require"]))
    if a.check:
        cur = json.load(io.open(a.out, encoding="utf-8-sig"))
        drift = []
        for k, v in cur["instruments"].items():
            if v.get("sha256") != doc["instruments"][k]["sha256"]:
                drift.append(k)
        ts_path = os.path.join(REPO, "eval/rover/r512/taskset-r512.json")
        now = {t["tid"]: t["prompt_sha256"] for t in
               json.load(io.open(ts_path, encoding="utf-8-sig"))["tasks"]}
        if cur.get("prompt_sha256") != now:
            drift.append("prompt_sha256")
        if drift:
            print("[致命] 预注册漂移: %s ⇒ FAIL-CLOSED (须显式改预注册并留痕)" % drift)
            return 3
        print("PREREG_CHECK_OK 器具=%d 判据=%d 验收面=%s" %
              (len(cur["instruments"]), len(cur["criteria"]), cur["evidence_scope"]["require"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
