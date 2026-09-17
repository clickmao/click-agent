"""线性代数相关纯函数算子。

每个算子签名 ``op(args: dict) -> str``, 返回应写出的 stdout 文本 (末尾无换行)。
"""

from fractions import Fraction


def det(args: dict) -> str:
    """整数矩阵行列式 mod `mod` 的非负余数 (0 <= 结果 < mod)。

    用 Fraction 做高斯消元求精确行列式 (整数矩阵行列式必为整数),
    记录行交换符号, 主元的连乘积即行列式, 最后统一取模保证非负。
    n <= 4, 规模极小, 无需担心性能。
    """
    raw = [[int(v) for v in row] for row in args["matrix"]]
    mod = int(args["mod"])
    n = len(raw)

    matrix = [[Fraction(v) for v in row] for row in raw]
    sign = 1
    result = Fraction(1)
    for col in range(n):
        pivot = None
        for r in range(col, n):
            if matrix[r][col] != 0:
                pivot = r
                break
        if pivot is None:
            return "0"
        if pivot != col:
            matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
            sign = -sign
        pv = matrix[col][col]
        result *= pv
        for r in range(col + 1, n):
            if matrix[r][col] == 0:
                continue
            factor = matrix[r][col] / pv
            for c in range(col, n):
                matrix[r][c] -= factor * matrix[col][c]

    assert result.denominator == 1, "整数矩阵行列式应为整数"
    value = sign * int(result)
    return str(value % mod)
