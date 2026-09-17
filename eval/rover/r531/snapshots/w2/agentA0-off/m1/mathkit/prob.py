"""Probability ops. Each op is a pure function op(args: dict) -> str."""

from fractions import Fraction


def expect(args: dict) -> str:
    """Expected number of red balls drawn without replacement.

    red + blue balls total, draw balls taken; expectation = draw * red / (red+blue),
    reported as a reduced fraction p/q (integers as k/1).
    """
    red = int(args["red"])
    blue = int(args["blue"])
    draw = int(args["draw"])
    total = red + blue
    frac = Fraction(draw * red, total)
    return f"{frac.numerator}/{frac.denominator}"
