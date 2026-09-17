#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""codex 外侧臂引擎加载器 —— 稳定位置 + 候选列表 + fail-closed。

动机 (R540 候选①): R534 减法批删除了 `eval/rover/r504/codex_solver_r504.py`, 而
`eval/rover/r508|r509|r511/proj_run_side*.py` 里 `load_codex_engine()` **硬编码**该路径 ⇒
ImportError 被上层吞掉后该臂**静默不可执行**(不报错, 只是没有 codex 读数)。教训:
"删器具必查跨轮调用点" 只靠人工 ⇒ 提为机制 (tools/refactor/delete_ref_gate.py)。

本模块:
  resolve(candidates)  — 返回首个存在且非空的跑器路径; 全缺 ⇒ raise SolverMissing(逐条点名候选)
  load(candidates)     — importlib 载入 resolve() 结果, 并**校验接口**(必须有 run_one)
  --check [--solver P] — CLI 机检: rc 0 = 可加载 / 3 = fail-closed (缺失或接口不符)

覆盖顺序: 环境变量 AGENTFRAMEWORK_CODEX_SOLVER > 稳定位置 eval/rover/lib/codex_solver.py >
历史轮副本 (只读回退, 不修改历史轮目录)。
"""
from __future__ import annotations
import argparse, importlib.util, io, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
STABLE = "eval/rover/lib/codex_solver.py"
FALLBACKS = [
    "eval/rover/r539/codex_solver_r539.py",
    "eval/rover/r511/codex_solver_r511.py",
    "eval/rover/r504/codex_solver_r504.py",
]
REQUIRED_API = ("run_one",)


class SolverMissing(RuntimeError):
    def __init__(self, tried):
        self.tried = list(tried)
        msg = "codex 跑器不可用 (fail-closed); 逐条候选: " + " | ".join(
            "%s=%s" % (p, "缺" if not os.path.exists(p) else "空") for p in self.tried)
        super().__init__(msg)


def candidates(override=None):
    """覆盖具**排他性**: 显式指定(--solver 或 AGENTFRAMEWORK_CODEX_SOLVER)时只认该路径 ——
    缺失即 fail-closed, 禁静默回退到别的引擎(否则读数归属不可追溯)。未指定 ⇒ 稳定位置 + 历史轮回退。"""
    ov = override or os.environ.get("AGENTFRAMEWORK_CODEX_SOLVER")
    if ov:
        return [ov]
    out = [os.path.join(REPO, STABLE)]
    out.extend(os.path.join(REPO, p) for p in FALLBACKS)
    return out


def resolve(override=None):
    tried = candidates(override)
    for p in tried:
        if os.path.isfile(p) and os.path.getsize(p) > 0:
            return p
    raise SolverMissing(tried)


def load(override=None):
    p = resolve(override)
    spec = importlib.util.spec_from_file_location("codex_solver_loaded", p)
    if spec is None or spec.loader is None:
        raise SolverMissing([p])
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    missing = [a for a in REQUIRED_API if not callable(getattr(m, a, None))]
    if missing:
        raise SolverMissing(["%s (缺接口 %s)" % (p, ",".join(missing))])
    m.__dict__["__solver_path__"] = p
    return m


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--solver", default=None, help="显式覆盖 (负控用: 指向不存在路径)")
    ap.add_argument("--json", dest="jout", default=None)
    a = ap.parse_args(argv)
    res = {"stable": os.path.join(REPO, STABLE), "candidates": candidates(a.solver), "rc": 0, "error": None}
    try:
        m = load(a.solver)
        res["resolved"] = m.__solver_path__
        res["api"] = {k: callable(getattr(m, k, None)) for k in REQUIRED_API}
        print("OK   codex 引擎可加载: %s (api=%s)" % (res["resolved"], res["api"]))
    except SolverMissing as e:
        res["rc"] = 3
        res["error"] = str(e)
        print("RED  " + str(e))
    if a.jout:
        with io.open(a.jout, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1)
    return res["rc"]


if __name__ == "__main__":
    sys.exit(main())
