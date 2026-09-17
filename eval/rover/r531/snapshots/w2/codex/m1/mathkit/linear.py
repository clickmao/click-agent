"""Linear algebra over prime moduli."""


def det(args: dict) -> str:
    mod = int(args["mod"])
    matrix = [[int(v) % mod for v in row] for row in args["matrix"]]
    n = len(matrix)
    result = 1
    for col in range(n):
        pivot = None
        for row in range(col, n):
            if matrix[row][col] % mod:
                pivot = row
                break
        if pivot is None:
            return "0"
        if pivot != col:
            matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
            result = -result
        inv = pow(matrix[col][col], mod - 2, mod)
        result = (result * matrix[col][col]) % mod
        for row in range(col + 1, n):
            factor = (matrix[row][col] * inv) % mod
            if factor:
                for j in range(col, n):
                    matrix[row][j] = (matrix[row][j] - factor * matrix[col][j]) % mod
    return str(result % mod)
