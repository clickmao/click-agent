"""概率相关 op：expect。每个 op 导出 op(args: dict) -> str。"""

from fractions import Fraction


def expect(args: dict) -> str:
    """袋中 red 红球 + blue 蓝球，不放回抽 draw 个；抽出红球个数的数学期望，最简分数 p/q。

    线性性: E = draw * red / (red + blue)。
    """
    red = int(args["red"])
    blue = int(args["blue"])
    draw = int(args["draw"])
    total = red + blue
    frac = Fraction(draw * red, total)
    return f"{frac.numerator}/{frac.denominator}"
