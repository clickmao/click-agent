"""Modular-arithmetic ops."""

from math import comb


def qr_count(args: dict) -> str:
    """Count roots of x^2 = a (mod m) with 0 <= x < m."""
    a = int(args["a"])
    m = int(args["m"])
    count = 0
    for x in range(m):
        r = (x * x - a) % m
        if r == 0:
            count += 1
    return str(count)


def choose(args: dict) -> str:
    """C(n, k) mod p, non-negative residue."""
    n = int(args["n"])
    k = int(args["k"])
    mod = int(args["mod"])
    return str(comb(n, k) % mod)
