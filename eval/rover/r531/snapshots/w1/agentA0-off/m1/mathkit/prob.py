"""Probability ops: expectation of the number of red balls drawn."""

from fractions import Fraction


def expect(args: dict) -> str:
    """Expected number of red balls when drawing ``draw`` balls without
    replacement from an urn with ``red`` red and ``blue`` blue balls.

    By linearity of expectation the answer is draw * red / (red + blue),
    returned as a reduced fraction ``p/q`` (integers rendered as ``k/1``).
    """
    red = int(args["red"])
    blue = int(args["blue"])
    draw = int(args["draw"])
    value = Fraction(draw * red, red + blue)
    return "%d/%d" % (value.numerator, value.denominator)
