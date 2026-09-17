"""Probability op: `expect` (expectation of red balls drawn without replacement)."""

from fractions import Fraction
from math import comb
from typing import Dict


def expect(args: Dict) -> str:
    """Expected number of red balls when drawing `draw` of red+blue.

    Linearity of expectation: each of the `draw` positions is red with
    probability red/(red+blue). Result is reduced as p/q (integers -> k/1).
    """
    red = int(args["red"])
    blue = int(args["blue"])
    draw = int(args["draw"])
    total = red + blue
    if draw < 0 or draw > total:
        raise ValueError("draw out of range")
    if total == 0:
        return "0/1"

    # Guarded sanity: also equal to the hypergeometric mean sum, which we
    # cross-check for small inputs below.
    value = Fraction(red, total) * draw

    # Independent cross-check via the hypergeometric distribution.
    # sum_{k} k * C(red,k)C(blue,draw-k)/C(total,draw)
    check = Fraction(0)
    for k in range(max(0, draw - blue), min(red, draw) + 1):
        check += Fraction(k * comb(red, k) * comb(blue, draw - k), comb(total, draw))
    if check != value:
        raise AssertionError("expectation mismatch")

    return f"{value.numerator}/{value.denominator}"
