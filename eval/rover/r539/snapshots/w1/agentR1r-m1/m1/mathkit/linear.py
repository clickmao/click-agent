"""Linear algebra over prime fields: modular determinant."""


def det(args: dict) -> str:
    """Determinant of an integer matrix, modulo `mod`, non-negative remainder."""
    matrix = [list(row) for row in args["matrix"]]
    mod = int(args["mod"])
    n = len(matrix)
    result = 1
    for col in range(n):
        pivot = None
        for row in range(col, n):
            if matrix[row][col] % mod != 0:
                pivot = row
                break
        if pivot is None:
            return "0"
        if pivot != col:
            matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
            result = -result
        result = (result * matrix[col][col]) % mod
        inv = pow(matrix[col][col] % mod, mod - 2, mod)
        for row in range(col + 1, n):
            if matrix[row][col] % mod == 0:
                continue
            factor = (matrix[row][col] * inv) % mod
            for c in range(col, n):
                matrix[row][c] = (matrix[row][c] - factor * matrix[col][c]) % mod
    return str(result % mod)
