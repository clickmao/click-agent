"""线性代数相关 op：det（整数矩阵行列式取模）。

纯函数，无 I/O，无第三方依赖。
"""


def det(args: dict) -> str:
    """整数矩阵行列式 mod `mod` 的非负余数（0 <= 结果 < mod）。

    参数: matrix（n×n 整数二维数组, 2<=n<=4）, mod（素数）。
    返回: 非负余数的十进制字符串。

    先用精确整数运算（Bareiss 无除法的朴素展开 / 分数消元）求 determinant，
    再对 mod 取非负余数，避免模运算中除法的可逆性问题。
    """
    matrix = [[int(v) for v in row] for row in args["matrix"]]
    mod = int(args["mod"])
    n = len(matrix)
    d = _det_exact(matrix, n)
    return str(d % mod)


def _det_exact(matrix, n: int) -> int:
    """精确整数行列式（分数消元，主元为 0 时换行；全部为 0 则行列式为 0）。"""
    m = [row[:] for row in matrix]
    sign = 1
    det_val = 1
    # 用 Fraction 保证精确，避免浮点。
    from fractions import Fraction

    fm = [[Fraction(v) for v in row] for row in m]
    for col in range(n):
        pivot = None
        for r in range(col, n):
            if fm[r][col] != 0:
                pivot = r
                break
        if pivot is None:
            return 0
        if pivot != col:
            fm[col], fm[pivot] = fm[pivot], fm[col]
            sign = -sign
        pv = fm[col][col]
        det_val *= pv
        for r in range(col + 1, n):
            factor = fm[r][col] / pv
            if factor == 0:
                continue
            for c in range(col, n):
                fm[r][c] -= factor * fm[col][c]
    # det = sign * product of pivots（这里用乘积求出的整数与符号）
    val = det_val
    if val.denominator != 1:
        # 行列式必为整数；若出现非整数说明逻辑异常，退回精确展开。
        return _det_recursive(matrix, n)
    return sign * int(val)


def _det_recursive(matrix, n: int) -> int:
    """拉普拉斯展开，纯整数，作为兜底实现。"""
    if n == 1:
        return matrix[0][0]
    if n == 2:
        return matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]
    total = 0
    for col in range(n):
        minor = [
            [matrix[r][c] for c in range(n) if c != col]
            for r in range(1, n)
        ]
        total += ((-1) ** col) * matrix[0][col] * _det_recursive(minor, n - 1)
    return total
