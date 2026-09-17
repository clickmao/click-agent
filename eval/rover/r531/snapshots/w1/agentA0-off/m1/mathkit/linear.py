"""Linear-algebra ops: modular determinant."""


def det(args: dict) -> str:
    """Integer determinant of an n x n matrix (2 <= n <= 4) modulo ``mod``.

    Gaussian elimination with exact fraction-free (Bareiss) arithmetic to keep
    the intermediate integers small, then reduce mod ``mod``.  ``mod`` is prime
    but divisibility by it is avoided by doing exact integer elimination first.
    """
    matrix = [[int(v) for v in row] for row in args["matrix"]]
    mod = int(args["mod"])
    n = len(matrix)

    sign = 1
    prev = 1
    a = [row[:] for row in matrix]

    # Bareiss algorithm: exact integer intermediate values, no division by mod.
    for k in range(n - 1):
        if a[k][k] == 0:
            pivot = None
            for r in range(k + 1, n):
                if a[r][k] != 0:
                    pivot = r
                    break
            if pivot is None:
                return "0"
            a[k], a[pivot] = a[pivot], a[k]
            sign = -sign
        for i in range(k + 1, n):
            for j in range(k + 1, n):
                a[i][j] = (a[i][j] * a[k][k] - a[i][k] * a[k][j]) // prev
            a[i][k] = 0
        prev = a[k][k]

    result = sign * a[n - 1][n - 1]
    return str(result % mod)
