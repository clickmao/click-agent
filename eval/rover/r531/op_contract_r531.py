#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R531 F3 (mathkit-multimodule-v1) 的**唯一契约源**。

一份契约被三处共用, 禁各自复制 (复制 = 漂移源):
  · `build_fixture_r531.py` —— 生成用例 (期望值由 `tasks.MATH_FAMILIES[*]['ref']` 产出);
  · `cases/run_cases_r531_math.py` —— 判分器 B 用 `[*]['check']` 独立重算 (非同源第二判据);
  · 正控 oracle 树 —— 用 `ref` + `fmt` 拼出参考实现。

契约面 (题面逐字采用本表):
  · CLI: `python3 -m mathkit <op>`; 参数 = **stdin 上的一个 JSON 对象**;
  · 输出: 恰好一行, 只含答案本身 (整数 / `-1` / 最简分数 `p/q`), 无前缀无空格。
"""
from __future__ import annotations

# op -> (所属模块, 生成器家族, args(JSON) -> 生成器 params 元组, 规格文本, 示例入参)
OP_TABLE = {
    "qr_count": {
        "mod": "modular",
        "family": "quadratic_residue_count",
        "params": lambda a: (int(a["a"]), int(a["m"])),
        "spec": "同余方程 x^2 ≡ a (mod m) 在 0 <= x < m 内的整数解个数。",
        "fields": "`a`(整数, 0..12), `m`(整数, 8..16)",
        "demo": {"a": 3, "m": 10},
    },
    "choose": {
        "mod": "modular",
        "family": "comb_mod",
        "params": lambda a: (int(a["n"]), int(a["k"]), int(a["mod"])),
        "spec": "组合数 C(n, k) mod `mod` 的非负余数 (0 <= 结果 < mod)。",
        "fields": "`n`(整数, 0..40), `k`(整数, 0..n), `mod`(素数 97/101/1000003)",
        "demo": {"n": 10, "k": 3, "mod": 97},
    },
    "det": {
        "mod": "linear",
        "family": "det_mod",
        "params": lambda a: ([[int(x) for x in row] for row in a["matrix"]], int(a["mod"])),
        "spec": "整数矩阵行列式 mod `mod` 的非负余数 (0 <= 结果 < mod)。",
        "fields": "`matrix`(n×n 整数二维数组, 2<=n<=4), `mod`(素数 97/101)",
        "demo": {"matrix": [[1, 2], [3, 4]], "mod": 97},
    },
    "shortest": {
        "mod": "graphs",
        "family": "shortest_path",
        "params": lambda a: ([[int(x) for x in row] for row in a["matrix"]], int(a["src"]), int(a["dst"]),
                             len(a["matrix"])),
        "spec": "带权无向图邻接矩阵 (0 = 无边, 对称) 上 `src` 到 `dst` 的最短路径长度; 不可达输出 -1。",
        "fields": "`matrix`(n×n 整数二维数组, 4<=n<=7), `src`(整数), `dst`(整数)",
        "demo": {"matrix": [[0, 2, 0], [2, 0, 3], [0, 3, 0]], "src": 0, "dst": 2},
    },
    "expect": {
        "mod": "prob",
        "family": "expectation_urn",
        "params": lambda a: (int(a["red"]), int(a["blue"]), int(a["draw"])),
        "spec": "袋中有 `red` 个红球与 `blue` 个蓝球, 不放回抽出 `draw` 个; 抽出红球个数的数学期望, "
                "以最简分数 p/q 给出 (整数也写成 `k/1`)。",
        "fields": "`red`(整数, 1..6), `blue`(整数, 1..6), `draw`(整数, 1..red+blue)",
        "demo": {"red": 2, "blue": 2, "draw": 2},
    },
}

# 模块 -> 该模块导出的 op 列表 (结构 = 4 模块 5 op; 逐模块可测: 每个 op 一条独立 CLI 调用)
MODULES = {
    "modular": ["qr_count", "choose"],
    "linear": ["det"],
    "graphs": ["shortest"],
    "prob": ["expect"],
}


def ops_of(module: str):
    return list(MODULES[module])


def all_ops():
    return list(OP_TABLE)


def to_params(op: str, args: dict):
    return OP_TABLE[op]["params"](args)
