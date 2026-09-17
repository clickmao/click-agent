"""概率论相关纯函数算子。

每个算子签名 ``op(args: dict) -> str``, 返回应写出的 stdout 文本 (末尾无换行)。
"""

from fractions import Fraction
from math import comb


def expect(args: dict) -> str:
    """不放回抽取 `draw` 个球时红球个数的数学期望, 以最简分数 p/q 给出。

    红球个数 X 服从超几何分布, E[X] = draw * red / (red + blue)。
    用 Fraction 归一化为最简分数, 整数写成 k/1。
    """
    red = int(args["red"])
    blue = int(args["blue"])
    draw = int(args["draw"])
    total = red + blue
    e = Fraction(draw * red, total)
    return f"{e.numerator}/{e.denominator}"
