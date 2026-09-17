"""数论 / 同余相关纯函数算子。

每个算子签名 ``op(args: dict) -> str``, 返回应写出的 stdout 文本 (末尾无换行)。
"""

from math import comb


def qr_count(args: dict) -> str:
    """同余方程 x^2 ≡ a (mod m) 在 0 <= x < m 内的整数解个数。

    枚举 0..m-1 逐个判定, 规模极小 (m <= 16), 无需数论化简。
    """
    a = int(args["a"])
    m = int(args["m"])
    count = 0
    for x in range(m):
        if (x * x - a) % m == 0:
            count += 1
    return str(count)


def choose(args: dict) -> str:
    """组合数 C(n, k) mod `mod` 的非负余数 (0 <= 结果 < mod)。

    直接使用精确组合数 (Python 大整数) 再取模, 避免逆元等边界问题;
    n <= 40 时 C(40,20) 量级完全可控。
    """
    n = int(args["n"])
    k = int(args["k"])
    mod = int(args["mod"])
    return str(comb(n, k) % mod)
