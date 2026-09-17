#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R519 夹具生成器: 由 R505 四款游戏(p001-p004, 含 public/hidden 用例) 合成
一个**多文件长任务**题面: games 包 + 分派入口。规格文本逐字复用 R505(v1 无改动)。"""
import json, os, sys

REPO = "/home/agentuser/AgentFramework"
R = os.path.join(REPO, "eval/rover/r519")
SRC = os.path.join(REPO, "eval/rover/r505/taskset-r505.json")
GAMES = [("life", "p001", "康威生命游戏 H 代演化"), ("sub", "p002", "取石子子游戏必败/必胜判定"),
         ("nim", "p003", "多堆 Nim 必胜手"), ("wythoff", "p004", "Wythoff 博弈必败点判定")]

src = json.load(open(SRC, encoding="utf-8"))
ts = src["tasks"] if isinstance(src, dict) else src
by = {t["tid"]: t for t in ts}

specs, cases = [], []
for gid, tid, desc in GAMES:
    t = by[tid]
    body = t["prompt"].split("【任务】", 1)[1].strip()
    specs.append("### 游戏 `%s`（%s）\n%s" % (gid, desc, body))
    for c in t["public"]:
        cases.append({"game": gid, "stdin": c["stdin"], "expected_stdout": c["expected_stdout"], "vis": "public"})
    for c in t["hidden"]:
        cases.append({"game": gid, "stdin": c["stdin"], "expected_stdout": c["expected_stdout"], "vis": "hidden"})

prompt = """用 Python 3 实现一个**多文件游戏包** `games/`（本任务规模超出单轮步数上限, 必须分模块完成）。

【结构要求】
- `games/__init__.py`：包初始化（可空, 但必须存在）
- `games/life.py`、`games/sub.py`、`games/nim.py`、`games/wythoff.py`：每款游戏一个模块, 各自导出 `solve(text: str) -> str`（纯函数: 入参=该游戏的完整 stdin 文本, 返回=应当写出的 stdout 文本, 末尾不带换行）
- `games/__main__.py`：CLI 入口, 使 `python3 -m games <game_id>` 可用（`<game_id>` 取 life/sub/nim/wythoff）；从标准输入读取全部文本、调用对应模块的 `solve`、把返回值写到标准输出
- 只允许标准库；不得打印任何多余文字、提示或调试信息（stderr 亦须静默）

【评分】对四款游戏分别用 `python3 -m games <game_id>` 跑隐藏用例, 逐字节比对 stdout。

【各游戏规格（逐字）】
%s
""" % "\n\n".join(specs)

os.makedirs(os.path.join(R, "cases"), exist_ok=True)
json.dump({"round": "R519", "family": "games-longtask-v1", "source": "eval/rover/r505/taskset-r505.json",
           "tasks": [{"tid": "g1", "kind": "program", "family": "games-longtask-v1", "prompt": prompt,
                      "cases": cases, "meta": {"n_games": len(GAMES), "n_cases": len(cases)}}]},
          open(os.path.join(R, "taskset-r519.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# 计划面: 5 节点 (每个模块 1 节点 + 分派入口 1 节点), 串行依赖
nodes = [("n1", "", "games/life.py", "实现 games/life.py 的 solve(text): 康威生命游戏演化"),
         ("n2", "n1", "games/sub.py", "实现 games/sub.py 的 solve(text): 子游戏必胜/必败判定"),
         ("n3", "n2", "games/nim.py", "实现 games/nim.py 的 solve(text): 多堆 Nim 必胜手"),
         ("n4", "n3", "games/wythoff.py", "实现 games/wythoff.py 的 solve(text): Wythoff 必败点判定"),
         ("n5", "n4", "games/__init__.py, games/__main__.py", "实现包初始化与 CLI 分派 python3 -m games <game_id>")]
plan = ["# R519 计划 (R516 NodePlanFile DSL): nodeId | dependsOn | exec | 输入 | 任务"]
scope = ["# R519 写范围声明 (R516 NodeScopeFile DSL): nodeId | 路径[,路径]"]
for nid, dep, files, text in nodes:
    plan.append(" | ".join([nid, dep, "remote", "", text]))
    scope.append("%s | %s" % (nid, files))
open(os.path.join(R, "plan-games-longtask.txt"), "w", encoding="utf-8").write("\n".join(plan) + "\n")
open(os.path.join(R, "scope-games-longtask.txt"), "w", encoding="utf-8").write("\n".join(scope) + "\n")
print("WROTE taskset-r519.json prompt_len=%d cases=%d (public=%d hidden=%d) nodes=%d"
      % (len(prompt), len(cases), sum(1 for c in cases if c["vis"] == "public"),
         sum(1 for c in cases if c["vis"] == "hidden"), len(nodes)))
