"""games: 四款组合博弈 / 生命游戏的小包。

每个子模块导出纯函数 solve(text: str) -> str,
其中 text 是该游戏的完整 stdin 文本, 返回值是应当写出的 stdout 文本
(末尾不带换行)。
"""

__all__ = ["life", "sub", "nim", "wythoff"]
