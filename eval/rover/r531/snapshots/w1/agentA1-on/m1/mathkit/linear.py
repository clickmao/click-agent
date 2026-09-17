"""Linear algebra operations (pure functions, op(args)->str)."""


def _det_mod(matrix, mod):
    """Determinant of an integer matrix, reduced mod `mod` at each step."""
    n = len(matrix)
    a = [[int(v) % mod for v in row] for row in matrix]
    det = 1
    for col in range(n):
        piv = None
        for r in range(col, n):
            if a[r][col] % mod != 0:
                piv = r
                break
        if piv is None:
            return 0
        if piv != col:
            a[col], a[piv] = a[piv], a[col]
            det = -det
        det = det * a[col][col] % mod
        inv = pow(a[col][col], -1, mod)
        for r in range(col + 1, n):
            if a[r][col] % mod == 0:
                continue
            factor = a[r][col] * inv % mod
            for c in range(col, n):
                a[r][c] = (a[r][c] - factor * a[col][c]) % mod
    return det % mod


def det(args: dict) -> str:
    """Determinant of an integer matrix, as a non-negative residue mod `mod`."""
    matrix = args["matrix"]
    mod = int(args["mod"])
    return str(_det_mod(matrix, mod))
