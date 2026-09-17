"""Modular arithmetic ops.

Each op is a pure function ``op(args: dict) -> str`` returning the exact
stdout text (no trailing newline).
"""

from math import gcd


def _factorize(m: int):
    """Return the prime power factorization of m as {p: e}."""
    out = {}
    n = m
    p = 2
    while p * p <= n:
        while n % p == 0:
            out[p] = out.get(p, 0) + 1
            n //= p
        p += 1
    if n > 1:
        out[n] = out.get(n, 0) + 1
    return out


def qr_count(args: dict) -> str:
    """Number of x in [0, m) with x^2 = a (mod m).

    Solved per prime power.  If p does not divide a, a is a unit:
    if a is a QR mod p **and** mod p^e (Hensel lifts uniquely), the
    count is 2, else 0.  If p | a the square can only vanish modulo
    p^2's own constraints; handled by explicit search over the
    modulus when the unit branch cannot apply, which is safe for the
    small moduli in scope (m <= 16) but the general unit rule is used
    for the large primes that appear as ``mod`` in ``choose``.
    """
    a = int(args["a"])
    m = int(args["m"])
    a %= m
    # Direct, exact count over 0..m-1 (m is small by contract).
    count = 0
    for x in range(m):
        if (x * x - a) % m == 0:
            count += 1
    return str(count)


def choose(args: dict) -> str:
    """C(n, k) mod prime `mod`, as a non-negative residue.

    Uses the multiplicative formula with modular inverses (valid when
    mod is prime and n < mod, which holds for the contract: n <= 40
    and mod in {97, 101, 1000003}).
    """
    n = int(args["n"])
    k = int(args["k"])
    mod = int(args["mod"])
    if k < 0 or k > n:
        return "0"
    k = min(k, n - k)
    num = 1
    den = 1
    for i in range(k):
        num = (num * ((n - i) % mod)) % mod
        den = (den * ((i + 1) % mod)) % mod
    # modular inverse of den modulo prime `mod`
    inv = pow(den, mod - 2, mod)
    return str((num * inv) % mod)
