"""Modular arithmetic ops (pure functions, op(args: dict) -> str)."""


def qr_count(args: dict) -> str:
    """Count x in [0, m) with x^2 == a (mod m)."""
    a = int(args["a"])
    m = int(args["m"])
    count = 0
    for x in range(m):
        if (x * x - a) % m == 0:
            count += 1
    return str(count)


def choose(args: dict) -> str:
    """C(n, k) mod prime `mod`, as a non-negative residue."""
    n = int(args["n"])
    k = int(args["k"])
    mod = int(args["mod"])
    if k < 0 or k > n:
        return "0"
    # Multiplicative formula with modular inverses (mod is prime).
    k = min(k, n - k)
    num = 1
    den = 1
    for i in range(1, k + 1):
        num = (num * (n - k + i)) % mod
        den = (den * i) % mod
    return str((num * pow(den, mod - 2, mod)) % mod)
