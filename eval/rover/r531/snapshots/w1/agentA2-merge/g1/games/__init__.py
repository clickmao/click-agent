"""games —— 四款经典组合博弈 / 元胞自动机的标准库实现包。

子模块:
    life     康威生命游戏 H 代演化
    sub      取石子子游戏 (减法博弈) 必胜/必败判定
    nim      多堆 Nim 必胜手
    wythoff  Wythoff 博弈必败点判定

每个子模块导出纯函数 ``solve(text: str) -> str``:
入参为该游戏的完整 stdin 文本, 返回为应当写出的 stdout 文本 (末尾不带换行)。
"""
