"""Linear-algebra ops."""


def det(args: dict) -> str:
    """Determinant of an integer matrix modulo `mod`, non-negative."""
    matrix = [[int(v) for v in row] for row in args["matrix"]]
    mod = int(args["mod"])
    n = len(matrix)
    a = [[matrix[i][j] % mod for j in range(n)] for i in range(n)]
    result = 1
    for col in range(n):
        pivot = None
        for row in range(col, n):
            if a[row][col] % mod:
                pivot = row
                break
        if pivot is None:
            return "0"
        if pivot != col:
            a[col], a[pivot] = a[pivot], a[col]
            result = -result
        result = result * a[col][col] % mod
        inv = pow(a[col][col], mod - 2, mod)
        for row in range(col + 1, n):
            if a[row][col]:
                factor = a[row][col] * inv % mod
                for j in range(col, n):
                    a[row][j] = (a[row][j] - factor * a[col][j]) % mod
    return str(result % mod)
