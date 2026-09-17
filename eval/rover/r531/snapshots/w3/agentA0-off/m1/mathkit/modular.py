"""模运算相关 op：qr_count、choose。每个 op 导出 op(args: dict) -> str。"""


def qr_count(args: dict) -> str:
    """同余方程 x^2 ≡ a (mod m) 在 0 <= x < m 内的整数解个数。

    入参: a(整数), m(整数 >0)。直接枚举全部剩余类，判定同余。
    """
    a = int(args["a"])
    m = int(args["m"])
    cnt = 0
    for x in range(m):
        if (x * x - a) % m == 0:
            cnt += 1
    return str(cnt)


def choose(args: dict) -> str:
    """组合数 C(n, k) mod `mod` 的非负余数 (0 <= 结果 < mod)。

    mod 为素数，但按通用做法用递推逐项取模，避免大整数溢出。
    """
    n = int(args["n"])
    k = int(args["k"])
    mod = int(args["mod"])
    if k < 0 or k > n:
        return "0"
    k = min(k, n - k)
    num = 1
    den = 1
    for i in range(1, k + 1):
        num = (num * (n - k + i)) % mod
        den = (den * i) % mod
    # mod 是素数，用费马小定理求逆元
    inv = pow(den, mod - 2, mod) if mod > 1 else 1
    return str((num * inv) % mod)
