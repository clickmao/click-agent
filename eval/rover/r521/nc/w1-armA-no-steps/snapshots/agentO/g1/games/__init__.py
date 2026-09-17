"""games —— 一组独立的小游戏求解器。

约定 (全包统一契约):
  * 每个子模块暴露一个 ``solve(text: str) -> str``, 从字符串读入, 返回字符串。
  * 子模块同时可作为脚本运行: ``python3 games/<game>.py`` (stdin -> stdout)。
  * 包入口: ``python3 -m games <game_id>`` (stdin -> stdout)。

game_id 表见 ``GAMES`` / ``GAME_IDS``。
"""

from __future__ import annotations

import importlib

# 包内的稳定公开面: game_id -> 模块名
GAMES = {
    "life": "games.life",
    "sub": "games.sub",
    "nim": "games.nim",
    "wythoff": "games.wythoff",
}

GAME_IDS = tuple(sorted(GAMES))

__all__ = ["GAMES", "GAME_IDS", "load_solver", "solve_game"]


def load_solver(game_id: str):
    """按 game_id 导入子模块并返回其 ``solve`` 函数。

    未知 game_id 抛 ``KeyError``; 子模块缺失 ``solve`` 抛 ``AttributeError``。
    """
    if game_id not in GAMES:
        raise KeyError(game_id)
    mod = importlib.import_module(GAMES[game_id])
    return getattr(mod, "solve")


def solve_game(game_id: str, text: str) -> str:
    """分派到指定游戏的 ``solve``。"""
    return load_solver(game_id)(text)
