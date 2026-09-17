"""Modular-arithmetic operations: qr_count, choose."""


def qr_count(args: dict) -> str:
    a = int(args["a"])
    m = int(args["m"])
    return str(sum(1 for x in range(m) if (x * x - a) % m == 0))


def choose(args: dict) -> str:
    n = int(args["n"])
    k = int(args["k"])
    mod = int(args["mod"])
    k = min(k, n - k)
    num = 1
    den = 1
    for i in range(k):
        num = (num * ((n - i) % mod)) % mod
        den = (den * (i + 1)) % mod
    return str((num * pow(den, mod - 2, mod)) % mod)
