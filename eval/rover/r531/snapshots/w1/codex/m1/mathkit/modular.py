"""Modular arithmetic operations (pure functions)."""

from math import comb


def qr_count(args: dict) -> str:
    a = int(args["a"])
    m = int(args["m"])
    a %= m
    return str(sum(1 for x in range(m) if (x * x - a) % m == 0))


def choose(args: dict) -> str:
    n = int(args["n"])
    k = int(args["k"])
    mod = int(args["mod"])
    return str(comb(n, k) % mod)
