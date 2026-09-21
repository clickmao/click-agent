"""games: 多游戏 CLI 包。

用法:
    python3 -m games <game_id>

game_id 取 life/sub/nim/wythoff；从 stdin 读全部文本，
把对应模块 solve(text) 的返回值写到 stdout（末尾不带换行）。
"""

GAMES = ("life", "sub", "nim", "wythoff")
