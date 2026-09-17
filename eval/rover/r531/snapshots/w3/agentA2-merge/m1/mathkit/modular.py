"""Modular arithmetic ops: `qr_count` and `choose`."""

from typing import Dict


def qr_count(args: Dict) -> str:
    """Count solutions of x^2 === a (mod m) with 0 <= x < m.

    Brute force over the residue set; correctness over cleverness since
    m <= 16 in the contract.
    """
    a = int(args["a"])
    m = int(args["m"])
    if m <= 0:
        raise ValueError("m must be positive")
    count = 0
    for x in range(m):
        if (x * x - a) % m == 0:
            count += 1
    return str(count)


def choose(args: Dict) -> str:
    """C(n, k) mod `mod` as a non-negative residue.

    Uses Pascal's rule by rows so no modular inverse is required (works
    for composite moduli too, though the contract only uses primes).
    """
    n = int(args["n"])
    k = int(args["k"])
    mod = int(args["mod"])
    if mod <= 0:
        raise ValueError("mod must be positive")
    if k < 0 or n < 0 or k > n:
        return "0"
    row = [0] * (k + 1)
    row[0] = 1 % mod
    for i in range(1, n + 1):
        # Descending update yields C(i, j) in place.
        for j in range(min(i, k), 0, -1):
            row[j] = (row[j] + row[j - 1]) % mod
    return str(row[k] % mod)
