"""线性代数相关 op：det。每个 op 导出 op(args: dict) -> str。"""


def det(args: dict) -> str:
    """整数矩阵行列式 mod `mod` 的非负余数 (0 <= 结果 < mod)。

    高斯消元取模；行交换时对结果取反（mod 下等价于 * -1）。
    """
    matrix = [[int(v) for v in row] for row in args["matrix"]]
    mod = int(args["mod"])
    n = len(matrix)
    a = [[matrix[i][j] % mod for j in range(n)] for i in range(n)]
    result = 1
    for col in range(n):
        pivot = -1
        for r in range(col, n):
            if a[r][col] % mod != 0:
                pivot = r
                break
        if pivot == -1:
            return "0"
        if pivot != col:
            a[col], a[pivot] = a[pivot], a[col]
            result = (-result) % mod
        result = (result * a[col][col]) % mod
        inv = pow(a[col][col], mod - 2, mod)
        for r in range(col + 1, n):
            if a[r][col] == 0:
                continue
            factor = (a[r][col] * inv) % mod
            for c in range(col, n):
                a[r][c] = (a[r][c] - factor * a[col][c]) % mod
    return str(result % mod)
