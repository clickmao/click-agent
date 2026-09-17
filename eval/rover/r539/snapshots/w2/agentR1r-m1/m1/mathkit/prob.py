"""Probability operations."""

from fractions import Fraction


def _comb(n, k):
    if k < 0 or k > n:
        return 0
    k = min(k, n - k)
    r = 1
    for i in range(1, k + 1):
        r = r * (n - k + i) // i
    return r


def expect(args):
    red = int(args["red"])
    blue = int(args["blue"])
    draw = int(args["draw"])
    total = red + blue
    num = 0
    den = _comb(total, draw)
    for r in range(0, min(red, draw) + 1):
        ways = _comb(red, r) * _comb(blue, draw - r)
        num += r * ways
    val = Fraction(num, den)
    return "%d/%d" % (val.numerator, val.denominator)
