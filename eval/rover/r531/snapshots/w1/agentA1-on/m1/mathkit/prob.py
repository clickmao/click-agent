"""Probability operations (pure functions, op(args)->str)."""

from fractions import Fraction
from math import comb


def expect(args: dict) -> str:
    """Expected number of red balls when drawing `draw` balls without
    replacement from an urn with `red` red and `blue` blue balls.

    Result is the reduced fraction p/q (integers rendered as k/1).
    """
    red = int(args["red"])
    blue = int(args["blue"])
    draw = int(args["draw"])
    total = red + blue
    frac = Fraction(draw * red, total)
    return "%d/%d" % (frac.numerator, frac.denominator)
