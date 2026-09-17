"""游戏包: 每款游戏一个模块, 各自导出 solve(text: str) -> str。

CLI 入口见 __main__.py, 用法: python3 -m games <game_id>
  game_id 取 life / sub / nim / wythoff
"""

__all__ = ["life", "sub", "nim", "wythoff"]
