"""Probability operations: expect."""

from fractions import Fraction


def expect(args: dict) -> str:
    red = int(args["red"])
    blue = int(args["blue"])
    draw = int(args["draw"])
    frac = Fraction(red, red + blue) * draw
    return f"{frac.numerator}/{frac.denominator}"
