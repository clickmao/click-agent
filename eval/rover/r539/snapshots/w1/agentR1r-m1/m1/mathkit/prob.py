"""Probability: expectation via exact rational arithmetic."""

import math
from fractions import Fraction


def expect(args: dict) -> str:
    """Expected number of red balls drawn in `draw` draws without replacement."""
    red = int(args["red"])
    blue = int(args["blue"])
    draw = int(args["draw"])
    total = red + blue
    value = Fraction(draw * red, total)
    if value.denominator == 1:
        return "%d/1" % value.numerator
    return "%d/%d" % (value.numerator, value.denominator)
