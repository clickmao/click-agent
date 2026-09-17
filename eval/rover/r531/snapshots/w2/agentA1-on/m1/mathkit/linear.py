"""Linear algebra ops.  Pure functions ``op(args: dict) -> str``."""


def det(args: dict) -> str:
    """Integer determinant mod prime `mod` (non-negative residue).

    Exact fraction-free elimination is unnecessary here: we do Gaussian
    elimination directly in the field Z/modZ (mod is prime, so every
    pivot is invertible unless it is 0).
    """
    matrix = [list(row) for row in args["matrix"]]
    mod = int(args["mod"])
    n = len(matrix)
    a = [[x % mod for x in row] for row in matrix]
    result = 1
    for col in range(n):
        # find pivot
        piv = -1
        for r in range(col, n):
            if a[r][col] % mod != 0:
                piv = r
                break
        if piv == -1:
            return "0"
        if piv != col:
            a[col], a[piv] = a[piv], a[col]
            result = (-result) % mod
        pv = a[col][col] % mod
        result = (result * pv) % mod
        inv = pow(pv, mod - 2, mod)
        for r in range(col + 1, n):
            f = (a[r][col] * inv) % mod
            if f:
                for c in range(col, n):
                    a[r][c] = (a[r][c] - f * a[col][c]) % mod
    return str(result % mod)
