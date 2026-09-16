#!/usr/bin/env python3
"""R505 预注册（**先于首跑**落盘; 哈希一律机取, 禁手抄）。

R505 主题 = 主线对照的**器具修复轮**（R504 实测缺陷: 判分后被后续作业覆盖 ⇒ 读数不可重放）+ n≥3 同窗质量面 + 判据② 逐题调用构成。

对象（与 R504 同题集 / 同外部真值 / 同 adapter ⇒ 可对照）:
    外部真值 = codex-cli（同一真实模型, 经同一 adapter）
    本侧     = AOT agenthost（probe `agent` 解法）
    输入     = 冻结题集（字节同 R504: taskset-r505.json 是 r504 题集的逐字节副本）
    判分     = eval/probe/grade.py 机械等值（禁模型裁判 / 禁事后补记）

用法:
    python3 make_prereg_r505.py            # 写 prereg_r505.json
    python3 make_prereg_r505.py --check    # 三态: rc=0 UNIFORM / rc=1 DRIFT / rc=3 MISSING
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PREREG = os.path.join(HERE, "prereg_r505.json")
CONFIG_MODEL = "deepseek-flash"
CODEX_BIN = os.path.expanduser("~/.agentframework/tools/codex-env/node_modules/.bin/codex")

WATCH = {
    "taskset": "eval/rover/r505/taskset-r505.json",
    "grade_py": "eval/probe/grade.py",
    "tasks_py": "eval/probe/tasks.py",
    "run_probe_py": "eval/probe/run_probe.py",
    "codex_solver_py": "eval/rover/r504/codex_solver_r504.py",
    "judge_py": "eval/rover/r505/judge_contrast_r505.py",
    "runner_sh": "eval/rover/r505/run_contrast_r505.sh",
    "nc_sh": "eval/rover/r505/nc_r505.sh",
    "adapter_py": "eval/rover/r455/adapter_tools.py",
    "attr_py": "eval/rover/r505/attr_calls_r505.py",
    "manifest_py": "eval/rover/r505/manifest_r505.py",
    "replay_py": "eval/rover/r505/check_usage_replay.py",
    "agg_py": "eval/rover/r505/agg_r505.py",
    "nc_instrument_sh": "eval/rover/r504/nc_r504.sh",
    "host_bin": os.environ.get("R505_HOST_BIN", "/tmp/pub_r504/agenthost/agenthost"),
}

CRITERIA = [
    "H1 仪器判别力（首跑前本地负控, 逐族两端）: 见 checks_prefirstrun.nc1*（oracle 满 ∧ 变体整题 0）—— 沿用 R504 判据器, R505 重跑取证",
    "H1g 器具判别力（R505 新增, 针对本轮修复的失败模式）: ① 命名空间守卫: 目标目录已被占用 ⇒ runner rc=4 且不启动任何作业; ② 污染检出器: 对「判分后被覆盖」的目录, 冻结清单复核必须 rc=2 并**点名**受影响文件; 干净副本必须 rc=0（两端都给, 只给一端不算自证）",
    "H1h 器具判别力（归因器）: 归因器对**已知构成**的历史调用（R504 幸存 8 条: p005/p006/p007/m001×2/m002/m003/m004）必须 8/8 归位且 0 未归因; 对无 tail_messages 的调用（codex 侧）必须记 unmatched（禁硬凑）",
    "H2 外部真值可用性: codex 侧 ok 题数 >= 1; 若 == 0 ⇒ 记 unreported（禁当 0 分能力、禁静默）",
    "H3 同输入机检: 两侧 probe 摘要 taskset_sha 相等且 == 预注册值; 且题集字节级等于 R504 v4 题集（跨轮同输入）",
    "H4 同模型机检: adapter 落盘 upstream_request.model 两侧一致; 单一模型名; 记本仓侧标签为对照标签",
    "H5 对照读数分列: 逐题 codex mode vs agent mode + 两侧 usage 分列; **禁**据 token 总量断言谁更省（静态面不同源）",
    "H6 fail-closed: 缺任一侧面产物/缺仓内快照 ⇒ rc=3（不得算绿）; codex 空回 ⇒ 记 no_code 单列",
    "H7 质量面 n≥3: 3 批同窗对照, 逐题 mode 一致率与整题全对数（每批 + 汇总）; 任一批质量面低于 R504 同题读数 ⇒ 回退触发器",
    "H8 逐题调用构成（判据② 取证）: 本侧每条调用必须归到 tid 或显式 fix 轮（unmatched==0 ∧ ambiguous==0）; codex 侧 raw 逐题 usage 必须与 adapter 观测总量逐位一致（不一致 ⇒ unreported, 禁猜）",
    "H9 证据可重放: 判分输入 = 仓内不可变快照; 同快照双读逐位相同; 运行内 + 日终两次 check_usage_replay 均须 rc=0",
    "H10 证据不可变: 快照逐文件 sha256 == 冻结清单; 任一不符 ⇒ 红并点名",
    "H11 反向控制（缺陷可检出）: 把 R504 的冻结 usage 清单喂给 R504 活目录 ⇒ check_usage_replay 必须 rc=2 且点名 9 个文件（证明修复针对的失败模式确实被机检捕获, 不是纸面声明）",
]

BOUNDARIES = [
    "codex 侧本机 bwrap 不可用 ⇒ 用 --dangerously-bypass-approvals-and-sandbox（审批/沙箱面不对等）",
    "两侧静态面不同源（instructions/工具面差异）⇒ 只比「同输入下的行为差异」与同侧趋势",
    "n=11 × 3 批（同一冻结题集）⇒ 质量面给同窗重跑一致性, 不构成总体能力估计",
    "跨轮禁相减（R504 与 R505 各自单窗读数; 只在同批内比较）",
    "R504 的 9 条本侧程序调用证据已被后续作业覆盖（本轮机检坐实）⇒ R504 的 17 调用构成**不可复原**, 只能作为「读一次」的历史读数",
]

LINEAGE = {
    "r504_evidence_sha256": {
        "verdict_txt": "eval/rover/r504/evidence/verdict-r504.txt",
        "adapter_usage_txt": "eval/rover/r504/evidence/adapter-usage.txt",
    },
    "defect": "adapter_tools.py 文件名计数是进程内计数器, DEMO_OUT 复用 ⇒ 同目录二次运行从 001 覆盖已判分证据 (R504: cand2_vmrun_n3.sh 覆盖 side-agent-001..009)",
    "fix": "① 命名空间守卫 (D/EV 空 + 端口不占) ② 阶段快照落仓内 ③ 逐文件 sha256 冻结清单 ④ 判分只读快照 ⑤ 冻结清单复核器 (check_usage_replay)",
}


def sha256(path: str):
    p = os.path.join(REPO, path)
    if not os.path.exists(p):
        return None
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def codex_version():
    if not os.path.exists(CODEX_BIN):
        return None
    try:
        p = subprocess.run([CODEX_BIN, "--version"], capture_output=True, text=True, timeout=60)
        s = (p.stdout or p.stderr).strip()
        return s.splitlines()[0] if s else None
    except Exception:
        return None


def probe_taskset_sha():
    try:
        sys.path.insert(0, os.path.join(REPO, "eval/probe"))
        import run_probe  # noqa: E402
        raw = json.load(open(os.path.join(REPO, "eval/rover/r505/taskset-r505.json"), encoding="utf-8"))
        return run_probe._canon_sha(raw)
    except Exception as e:
        print("WARN probe_taskset_sha 不可派生: %s" % e)
        return None


def taskset_oracle():
    want = probe_taskset_sha()
    best = hit = None
    for p in sorted(glob.glob(os.path.join(REPO, "data/probe/probe-oracle-*.json"))):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if d.get("taskset_sha") == want:
            best, hit = d, p
    if best is None or hit is None:
        return {"rate": None, "reading": "unreported: 无与本 taskset_sha 匹配的 oracle 摘要"}
    return {"rate": best.get("rate"), "passed": best.get("passed"), "total": best.get("total"),
            "n_tasks": len(best.get("per_task") or []), "taskset_sha": best.get("taskset_sha"),
            "solver": best.get("solver"), "src": os.path.relpath(hit, REPO)}


def taskset_meta():
    raw = json.load(open(os.path.join(REPO, "eval/rover/r505/taskset-r505.json"), encoding="utf-8"))
    fams = sorted({t["family"] for t in raw})
    r504 = sha256("eval/rover/r504/taskset-r504.json")
    return {"path": "eval/rover/r505/taskset-r505.json", "n_tasks": len(raw),
            "families": ",".join(fams), "game_family": "life_k,sub_game,nim_multi,wythoff",
            "kind_arg": "per-family-merge(以族定向 dump 后合并)", "seed": 20260917,
            "r504_sha256": r504, "byte_identical_to_r504": r504 == sha256("eval/rover/r505/taskset-r505.json"),
            "oracle_baseline": taskset_oracle()}


def build() -> dict:
    return {
        "round": "R505",
        "topic": "主线对照器具修复（证据快照/不可变/可重放）× n≥3 同窗质量面 × 判据② 逐题调用构成",
        "prereg_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "first_run": True,
        "external_reference": {
            "codex_bin": CODEX_BIN, "codex_version": codex_version(),
            "npm_package": "@openai/codex@0.154.0", "adapter": "eval/rover/r455/adapter_tools.py",
            "config_model_label": CONFIG_MODEL,
            "route": "codex/agent 两侧 -> http://127.0.0.1:<R505_ADAPTER_PORT>/v1 -> upstream",
            "n_calls": "unreported（本地对照跑不耗远端额度时仍按调用数列账; 两侧分列）",
        },
        "files_sha256": {k: sha256(v) for k, v in WATCH.items()},
        "probe_taskset_sha": probe_taskset_sha(),
        "taskset": taskset_meta(),
        "criteria": CRITERIA,
        "honest_boundaries": BOUNDARIES,
        "lineage": LINEAGE,
    }


def check() -> int:
    if not os.path.exists(PREREG):
        print("MISSING: 预注册文件不存在 %s" % PREREG)
        return 3
    old = json.load(open(PREREG, encoding="utf-8"))
    new = build()
    drift, missing = [], []
    for k in WATCH:
        o, n = (old.get("files_sha256") or {}).get(k), new["files_sha256"][k]
        if o is None or n is None:
            missing.append("%s (old=%s new=%s)" % (k, o, n))
        elif o != n:
            drift.append("%s: %s -> %s" % (k, o[:12], n[:12]))
    for key in ("criteria", "honest_boundaries", "external_reference"):
        if key not in old:
            missing.append(key)
    o_ts, n_ts = old.get("probe_taskset_sha"), new["probe_taskset_sha"]
    if o_ts is None or n_ts is None:
        missing.append("probe_taskset_sha(old=%s new=%s)" % (o_ts, n_ts))
    elif o_ts != n_ts:
        drift.append("probe_taskset_sha: %s -> %s" % (o_ts, n_ts))
    if missing:
        print("MISSING: %s" % "; ".join(missing))
        return 3
    if drift or old.get("external_reference", {}).get("codex_version") != new["external_reference"]["codex_version"]:
        print("DRIFT: %s" % ("; ".join(drift) or "codex_version 变化"))
        return 1
    print("UNIFORM: 预注册与当前树态一致（%d 件哈希 + %d 条判据 + 首跑前负控 %d 块）" % (
        len(WATCH), len(old.get("criteria") or []), len(old.get("checks_prefirstrun") or {})))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", default=PREREG)
    a = ap.parse_args()
    if a.check:
        return check()
    d = build()
    keep = None
    if os.path.exists(a.out):
        try:
            keep = json.load(open(a.out, encoding="utf-8")).get("checks_prefirstrun")
        except Exception:
            keep = None
    if keep:
        d["checks_prefirstrun"] = keep
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    miss = [k for k, v in d["files_sha256"].items() if v is None]
    print("prereg -> %s" % a.out)
    print("codex  = %s (%s)" % (d["external_reference"]["codex_version"], d["external_reference"]["npm_package"]))
    print("题集   = %s | n=%s | 与 R504 字节同 = %s" % (
        d["taskset"]["path"], d["taskset"]["n_tasks"], d["taskset"]["byte_identical_to_r504"]))
    print("哈希   = %d/%d 件" % (len(WATCH) - len(miss), len(WATCH)))
    if miss:
        print("WARN 缺件(哈希 None): %s" % ", ".join(miss))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
