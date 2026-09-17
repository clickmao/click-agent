"""Probability operations (pure functions)."""

from fractions import Fraction


def expect(args: dict) -> str:
    red = int(args["red"])
    blue = int(args["blue"])
    draw = int(args["draw"])
    value = Fraction(draw * red, red + blue)
    return f"{value.numerator}/{value.denominator}"
