"""Probability ops.  Pure functions ``op(args: dict) -> str``."""

from fractions import Fraction
from math import comb


def expect(args: dict) -> str:
    """Expected number of red balls in `draw` draws without replacement.

    By linearity of expectation each draw has probability red/(red+blue),
    so E = draw * red / (red + blue), reduced to lowest terms.
    """
    red = int(args["red"])
    blue = int(args["blue"])
    draw = int(args["draw"])
    e = Fraction(draw * red, red + blue)
    return "%d/%d" % (e.numerator, e.denominator)
