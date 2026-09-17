"""Linear-algebra ops. Each op is a pure function op(args: dict) -> str."""


def det(args: dict) -> str:
    """Determinant of an integer matrix, reduced mod prime `mod`."""
    matrix = [[int(v) for v in row] for row in args["matrix"]]
    mod = int(args["mod"])
    n = len(matrix)
    # Fraction-free-ish Gaussian elimination over the integers.
    a = [row[:] for row in matrix]
    sign = 1
    det_val = 1
    for col in range(n):
        pivot = None
        for r in range(col, n):
            if a[r][col] != 0:
                pivot = r
                break
        if pivot is None:
            det_val = 0
            break
        if pivot != col:
            a[col], a[pivot] = a[pivot], a[col]
            sign = -sign
        pv = a[col][col]
        det_val *= pv
        for r in range(col + 1, n):
            if a[r][col] == 0:
                continue
            factor = a[r][col]
            for c in range(col, n):
                a[r][c] = a[r][c] * pv - a[col][c] * factor
            det_val //= pv  # keep exact integer determinant
    return str((sign * det_val) % mod)
