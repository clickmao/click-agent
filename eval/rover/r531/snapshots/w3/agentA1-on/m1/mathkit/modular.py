"""模算术相关 op：qr_count（二次剩余解个数）、choose（组合数取模）。

均为纯函数，无 I/O，无第三方依赖。
"""

from math import gcd


def qr_count(args: dict) -> str:
    """同余方程 x^2 ≡ a (mod m) 在 0 <= x < m 内的整数解个数。

    参数: a（整数）, m（正整数）。
    返回: 解个数的十进制字符串。
    """
    a = int(args["a"])
    m = int(args["m"])
    count = 0
    for x in range(m):
        if (x * x - a) % m == 0:
            count += 1
    return str(count)


def choose(args: dict) -> str:
    """组合数 C(n, k) mod `mod` 的非负余数（0 <= 结果 < mod）。

    参数: n（0..40）, k（0..n）, mod（素数）。
    返回: 非负余数的十进制字符串。

    受 m 为素数的保证，用乘法逆元（费马小定理）精确计算，
    避免引入浮点误差；模为素数且 n < mod 时无因子被模消掉。
    """
    n = int(args["n"])
    k = int(args["k"])
    mod = int(args["mod"])
    if k < 0 or k > n:
        return "0"
    k = min(k, n - k)
    if k == 0:
        return str(1 % mod)

    # 分子 = (n-k+1) * ... * n ; 分母 = k!  (均在 mod 下求值后用逆元相除)
    num = 1
    den = 1
    for i in range(1, k + 1):
        num = (num * ((n - k + i) % mod)) % mod
        den = (den * (i % mod)) % mod

    if den % mod == 0:
        # 理论上在 n < mod 时不会发生；保守兜底用精确整数组合再取模。
        from math import comb
        return str(comb(n, k) % mod)

    inv = pow(den, -1, mod) if _supports_modinv() else pow(den, mod - 2, mod)
    return str((num * inv) % mod)


def _supports_modinv() -> bool:
    """Python 3.8+ 支持 pow(x, -1, m) 的模逆；否则退化为费马小定理。"""
    try:
        pow(2, -1, 97)
        return True
    except (TypeError, ValueError):
        return False


# 保留导入以便上游按需使用（纯函数模块，无副作用）。
_ = gcd
