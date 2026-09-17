"""概率相关 op：expect（超几何分布期望，最简分数）。

纯函数，无 I/O，无第三方依赖（fractions）。
"""

from fractions import Fraction
from math import comb


def expect(args: dict) -> str:
    """不放回抽 draw 个球时，抽出红球个数的数学期望。

    参数: red（1..6）, blue（1..6）, draw（1..red+blue）。
    返回: 最简分数 "p/q"（整数亦写作 "k/1"）。
    """
    red = int(args["red"])
    blue = int(args["blue"])
    draw = int(args["draw"])

    total = red + blue
    # 超几何分布：E[X] = draw * red / total。
    e = Fraction(draw * red, total)
    return f"{e.numerator}/{e.denominator}"


# 保留 comb 导入（期望的另一种等价算法），避免未使用告警带来的歧义。
_ = comb
