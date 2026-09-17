"""Probability ops."""

from fractions import Fraction
from math import comb


def expect(args: dict) -> str:
    """Expected number of red balls drawn without replacement."""
    red = int(args["red"])
    blue = int(args["blue"])
    draw = int(args["draw"])
    total = red + blue
    e = Fraction(draw * red, total)
    return "%d/%d" % (e.numerator, e.denominator)
