"""games —— 多游戏求解包 (零第三方依赖, 纯标准库)。

用法:
    python3 -m games <game_id>      # 从 STDIN 读整体输入, 结果写到 STDOUT
    python3 -m games --list         # 列出支持的 game_id
    python3 -m games --selftest     # 无头自检, 只打印 PASS/FAIL, 退出码 0/非 0

支持的 game_id:
    life      康威生命游戏演化          -> games/life.py::solve
    sub       子游戏必胜/必败判定        -> games/sub.py::solve
    nim       多堆 Nim 必胜手            -> games/nim.py::solve
    wythoff   Wythoff 必败点判定         -> games/wythoff.py::solve
    all       依次运行所有子游戏自检

各子游戏模块均导出 solve(text) -> str, 输入为 STDIN 整体文本,
输出为应写到 STDOUT 的文本 (不含任何多余调试信息)。
"""

from __future__ import annotations

__version__ = "1.0.0"

# game_id -> (模块名, 一句话说明)
GAMES = {
    "life": ("games.life", "康威生命游戏演化"),
    "sub": ("games.sub", "子游戏必胜/必败判定"),
    "nim": ("games.nim", "多堆 Nim 必胜手"),
    "wythoff": ("games.wythoff", "Wythoff 必败点判定"),
}

__all__ = ["GAMES", "__version__", "get_solver", "game_ids"]


def game_ids():
    """返回已登记的 game_id 升序列表 (副本, 调用方改不到内部字典)。"""
    return sorted(GAMES.keys())


def get_solver(game_id):
    """按 game_id 取 solve 可调用对象; 未知 id 抛 KeyError (附带可用列表)。"""
    if game_id not in GAMES:
        raise KeyError(
            "unknown game_id: %r; available: %s"
            % (game_id, ", ".join(game_ids()))
        )
    module_name, _desc = GAMES[game_id]
    module = __import__(module_name, fromlist=["solve"])
    return module.solve
