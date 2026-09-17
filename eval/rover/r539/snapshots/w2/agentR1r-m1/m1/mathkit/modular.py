"""Modular arithmetic operations."""


def qr_count(args):
    a = int(args["a"])
    m = int(args["m"])
    return str(sum(1 for x in range(m) if (x * x) % m == a % m))


def choose(args):
    n = int(args["n"])
    k = int(args["k"])
    mod = int(args["mod"])
    if k < 0 or k > n:
        return "0"
    k = min(k, n - k)
    c = 1
    for i in range(1, k + 1):
        c = (c * (n - k + i)) // i
    return str(c % mod)
