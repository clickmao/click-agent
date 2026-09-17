"""Linear-algebra operations: det."""


def det(args: dict) -> str:
    matrix = [[int(v) % int(args["mod"]) for v in row] for row in args["matrix"]]
    mod = int(args["mod"])
    n = len(matrix)
    sign = 1
    result = 1
    for col in range(n):
        pivot = None
        for r in range(col, n):
            if matrix[r][col] % mod != 0:
                pivot = r
                break
        if pivot is None:
            return "0"
        if pivot != col:
            matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
            sign = -sign
        result = (result * matrix[col][col]) % mod
        inv = pow(matrix[col][col], mod - 2, mod)
        for r in range(col + 1, n):
            factor = (matrix[r][col] * inv) % mod
            if factor:
                for c in range(col, n):
                    matrix[r][c] = (matrix[r][c] - factor * matrix[col][c]) % mod
    if sign < 0:
        result = (-result) % mod
    return str(result % mod)
