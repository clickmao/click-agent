"""Linear algebra operations over a prime modulus (pure functions)."""


def det(args: dict) -> str:
    matrix = [[int(v) for v in row] for row in args["matrix"]]
    mod = int(args["mod"])
    n = len(matrix)
    a = [[v % mod for v in row] for row in matrix]
    result = 1
    for col in range(n):
        piv = None
        for r in range(col, n):
            if a[r][col] % mod != 0:
                piv = r
                break
        if piv is None:
            return "0"
        if piv != col:
            a[col], a[piv] = a[piv], a[col]
            result = (-result) % mod
        inv = pow(a[col][col], mod - 2, mod)
        result = result * a[col][col] % mod
        for r in range(col + 1, n):
            factor = a[r][col] * inv % mod
            if factor:
                for c in range(col, n):
                    a[r][c] = (a[r][c] - factor * a[col][c]) % mod
    return str(result % mod)
