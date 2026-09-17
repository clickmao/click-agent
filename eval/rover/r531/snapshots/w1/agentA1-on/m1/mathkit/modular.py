"""Modular arithmetic operations (pure functions, op(args)->str)."""

from math import comb


def qr_count(args: dict) -> str:
    """Number of integer solutions of x^2 == a (mod m) with 0 <= x < m."""
    a = int(args["a"])
    m = int(args["m"])
    cnt = 0
    for x in range(m):
        if (x * x - a) % m == 0:
            cnt += 1
    return str(cnt)


def choose(args: dict) -> str:
    """Binomial coefficient C(n, k) as a non-negative residue mod `mod`."""
    n = int(args["n"])
    k = int(args["k"])
    mod = int(args["mod"])
    return str(comb(n, k) % mod)
