"""Probability ops (pure functions, op(args: dict) -> str)."""

from fractions import Fraction


def expect(args: dict) -> str:
    """Expected number of red balls when drawing `draw` from `red`+`blue`.

    Linear of expectation: each draw is red with probability red/(red+blue),
    so E = draw * red / (red + blue).  Returned as a reduced fraction p/q.
    """
    red = int(args["red"])
    blue = int(args["blue"])
    draw = int(args["draw"])
    total = red + blue
    e = Fraction(draw * red, total)
    return f"{e.numerator}/{e.denominator}"
