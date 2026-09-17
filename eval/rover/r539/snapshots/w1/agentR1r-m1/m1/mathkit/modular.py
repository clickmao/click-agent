"""Number-theoretic operations: quadratic residue counting and modular binomials."""

import math


def qr_count(args: dict) -> str:
    """Count integers x in [0, m) with x^2 == a (mod m)."""
    a = int(args["a"])
    m = int(args["m"])
    return str(sum(1 for x in range(m) if (x * x - a) % m == 0))


def choose(args: dict) -> str:
    """C(n, k) mod prime `mod`, non-negative remainder."""
    n = int(args["n"])
    k = int(args["k"])
    mod = int(args["mod"])
    return str(math.comb(n, k) % mod)
