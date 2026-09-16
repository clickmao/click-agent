#!/usr/bin/env python3
"""R503 预注册（**先于首跑**落盘；哈希一律机取，禁手抄 —— R483 令）。

对象 = 主线（外部对照自检）的一批对照跑:
    外部真值 = codex-cli（另一套真 agent 框架, 同一真实模型 deepseek-flash, 经同一 adapter）
    本侧     = AOT agenthost（probe `agent` 解法）
    输入     = 冻结随机题集（程序族 + 见证型数学族, 隐藏用例判定）
    判分     = eval/probe/grade.py 机械等值（禁模型裁判 / 禁事后补记）

用法:
    python3 make_prereg_r503.py            # 写 prereg_r503.json（机取哈希）
    python3 make_prereg_r503.py --check    # 三态: rc=0 UNIFORM / rc=1 DRIFT / rc=3 MISSING
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PREREG = os.path.join(HERE, "prereg_r503.json")

CODEX_BIN = os.path.expanduser("~/.agentframework/tools/codex-env/node_modules/.bin/codex")

WATCH = {
    "taskset": "eval/rover/r503/taskset-r503.json",
    "grade_py": "eval/probe/grade.py",
    "tasks_py": "eval/probe/tasks.py",
    "run_probe_py": "eval/probe/run_probe.py",
    "codex_solver_py": "eval/rover/r503/codex_solver_r503.py",
    "judge_py": "eval/rover/r503/judge_contrast_r503.py",
    "runner_sh": "eval/rover/r503/run_contrast_r503.sh",
    "nc_sh": "eval/rover/r503/nc_r503.sh",
    "adapter_py": "eval/rover/r455/adapter_tools.py",
}

CRITERIA = [
    "H1 仪器判别力（首跑前本地负控, 两端都要）: 程序面 json_mini×mutation:json_loose 整题全对 == 0 ∧ oracle == 1.0; 游戏族 life_k×mutation:life_wrap 整题全对 == 0 ∧ oracle == 1.0（只给一端不算自证）",
    "H1b 仪器判别力（R503 扩面新增族, 首跑前本地负控）: 游戏族 sub_game×mutation:sub_greedy 整题全对 == 0 ∧ oracle == 1.0（用例级 rate>0 属正常: 贪心在多数局面与最优手同值 —— 判红口径=整题, 见 nc_r503 注释）",
    "H2 外部真值可用性: codex 侧 ok 题数 >= 1；若 == 0 ⇒ 记 unreported（禁当 0 分能力、禁静默）",
    "H3 同输入机检: 两侧 probe 摘要 taskset_sha 相等且 == 预注册值（E2）",
    "H4 同模型机检: adapter 落盘 upstream_request.model 两侧均为 deepseek-flash（E3）",
    "H5 对照读数分列: 逐题 codex mode vs agent mode + 两侧 usage 分列成表；**禁**据 token 总量断言谁更省（静态面不同源）",
    "H6 fail-closed: 缺任一侧面产物 ⇒ rc=3（不得算绿）；codex 空回 ⇒ 记 no_code 且单列，不折算成 0 能力",
]

BOUNDARIES = [
    "codex 侧本机 bwrap 不可用 ⇒ 用 --dangerously-bypass-approvals-and-sandbox（审批/沙箱面不对等）",
    "两侧静态面不同源（instructions/工具面差异）⇒ 只比「同输入下的行为差异」与同侧趋势",
    "n=8（5 程序族: 含游戏族 life_k + sub_game 两族; 3 见证型数学族: sqrt_mod/min_counterexample/mod_inverse）为低成本首跑，不构成总体能力估计",
    "单窗单跑 ⇒ 跨轮禁相减",
]


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
        return (p.stdout or p.stderr).strip().splitlines()[0] if (p.stdout or p.stderr).strip() else None
    except Exception:
        return None


def probe_taskset_sha():
    """probe 内部口径的题集哈希 (_canon_sha, 见 run_probe.py:1100) —— 判据 H3 用的正是这个值。"""
    try:
        sys.path.insert(0, os.path.join(REPO, "eval/probe"))
        import run_probe  # noqa: E402
        raw = json.load(open(os.path.join(REPO, "eval/rover/r503/taskset-r503.json"), encoding="utf-8"))
        return run_probe._canon_sha(raw)
    except Exception as e:
        print("WARN probe_taskset_sha 不可派生: %s" % e)
        return None


def taskset_oracle():
    """冻结题集的正控基线 —— 从 data/probe/ 里挑 **taskset_sha 与本预注册一致** 的 oracle 摘要（禁跨题集引用）。"""
    want = probe_taskset_sha()
    best = None
    hit = None
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
    """题集元信息机取（禁硬编码轮内数字）。"""
    raw = json.load(open(os.path.join(REPO, "eval/rover/r503/taskset-r503.json"), encoding="utf-8"))
    fams = sorted({t["family"] for t in raw})
    return {"path": "eval/rover/r503/taskset-r503.json", "n_tasks": len(raw),
            "families": ",".join(fams), "game_family": "life_k,sub_game",
            "kind_arg": "per-family-merge(以族定向 dump 后合并)",
            "seed": 20260917, "oracle_baseline": taskset_oracle()}


def build() -> dict:
    return {
        "round": "R503",
        "topic": "主线对照（外部真值 codex-cli × 本侧 AOT）× 冻结随机题集 × 机械判分",
        "prereg_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"),
        "first_run": True,
        "external_reference": {
            "codex_bin": CODEX_BIN,
            "codex_version": codex_version(),
            "npm_package": "@openai/codex@0.154.0",
            "adapter": "eval/rover/r455/adapter_tools.py",
            "upstream_model": "deepseek-flash",
            "route": "codex/agent 两侧 -> http://127.0.0.1:<R503_ADAPTER_PORT>/v1 -> upstream",
        },
        "files_sha256": {k: sha256(v) for k, v in WATCH.items()},
        "probe_taskset_sha": probe_taskset_sha(),
        "taskset": taskset_meta(),
        "criteria": CRITERIA,
        "honest_boundaries": BOUNDARIES,
    }


def check() -> int:
    if not os.path.exists(PREREG):
        print("MISSING: 预注册文件不存在 %s" % PREREG)
        return 3
    old = json.load(open(PREREG, encoding="utf-8"))
    new = build()
    drift, missing = [], []
    for k, v in WATCH.items():
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
    print("UNIFORM: 预注册与当前树态一致（%d 件哈希 + %d 条判据）" % (len(WATCH), len(old.get("criteria") or [])))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", default=PREREG)
    a = ap.parse_args()
    if a.check:
        return check()
    d = build()
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    miss = [k for k, v in d["files_sha256"].items() if v is None]
    print("prereg -> %s" % a.out)
    print("codex  = %s (%s)" % (d["external_reference"]["codex_version"], d["external_reference"]["npm_package"]))
    print("哈希   = %d/%d 件" % (len(WATCH) - len(miss), len(WATCH)))
    if miss:
        print("WARN 缺件(哈希 None): %s" % ", ".join(miss))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
