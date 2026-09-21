"""games: 四款组合博弈/生命游戏的小型多模块包。

子模块:
    life   -- 康威生命游戏 H 代演化
    sub    -- 取石子子游戏必败/必胜判定
    nim    -- 多堆 Nim 必胜手
    wythoff-- Wythoff 博弈必败点判定

每个子模块导出纯函数 solve(text: str) -> str:
入参为该游戏的完整 stdin 文本, 返回应当写出的 stdout 文本(末尾不带换行)。

CLI: python3 -m games <life|sub|nim|wythoff>
"""

__all__ = ["life", "sub", "nim", "wythoff"]
