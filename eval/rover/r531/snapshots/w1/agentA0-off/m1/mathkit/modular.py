"""Modular-arithmetic ops: quadratic residue counting and modular binomials.

Every op is a pure function ``op(args: dict) -> str`` returning the exact
stdout text (no trailing newline).
"""


def qr_count(args: dict) -> str:
    """Number of solutions of x^2 == a (mod m) with 0 <= x < m.

    Brute force over the full residue range; m is small (8..16).
    """
    a = int(args["a"])
    m = int(args["m"])
    count = 0
    for x in range(m):
        if (x * x - a) % m == 0:
            count += 1
    return str(count)


def _mod_pow(base: int, exp: int, mod: int) -> int:
    return pow(base % mod, exp, mod)


def choose(args: dict) -> str:
    """C(n, k) mod ``mod`` as a non-negative residue.

    ``mod`` is prime (97 / 101 / 1000003); n <= 40 < mod, so no factorial
    ever vanishes modulo mod and plain multiplicative computation is exact.
    """
    n = int(args["n"])
    k = int(args["k"])
    mod = int(args["mod"])
    # Degenerate inputs outside the declared domain 0 <= k <= n are still
    # handled honestly: an impossible selection has zero combinations.
    if k < 0 or k > n:
        return "0"
    k = min(k, n - k)
    num = 1
    den = 1
    for i in range(k):
        num = (num * ((n - i) % mod)) % mod
        den = (den * ((i + 1) % mod)) % mod
    # Fermat inverse: mod is prime and den is coprime to it.
    inv = _mod_pow(den, mod - 2, mod)
    return str((num * inv) % mod)
