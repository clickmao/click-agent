"""Modular-arithmetic ops. Each op is a pure function op(args: dict) -> str."""


def qr_count(args: dict) -> str:
    """Number of x in [0, m) with x*x == a (mod m)."""
    a = int(args["a"])
    m = int(args["m"])
    cnt = 0
    for x in range(m):
        if (x * x - a) % m == 0:
            cnt += 1
    return str(cnt)


def choose(args: dict) -> str:
    """C(n, k) mod prime `mod`, non-negative residue."""
    n = int(args["n"])
    k = int(args["k"])
    mod = int(args["mod"])
    if k < 0 or k > n:
        return str(0 % mod)
    k = min(k, n - k)
    # exact combinatorial value, then reduce (n <= 40 so it stays small)
    num = 1
    den = 1
    for i in range(k):
        num *= (n - i)
        den *= (i + 1)
    return str((num // den) % mod)
