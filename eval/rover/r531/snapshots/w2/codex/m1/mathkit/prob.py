"""Probability computations."""
from math import comb
from fractions import Fraction


def expect(args: dict) -> str:
    red = int(args["red"])
    blue = int(args["blue"])
    draw = int(args["draw"])
    total = red + blue
    value = Fraction(0, 1)
    for r in range(0, min(red, draw) + 1):
        if draw - r > blue or draw - r < 0:
            continue
        p = Fraction(comb(red, r) * comb(blue, draw - r), comb(total, draw))
        value += r * p
    return f"{value.numerator}/{value.denominator}"
