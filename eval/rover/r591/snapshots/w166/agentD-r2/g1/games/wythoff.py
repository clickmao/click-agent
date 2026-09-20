def _lose(a, b):
    # Wythoff 必败点 (Beatty 序列): (floor(k*phi), floor(k*phi^2))
    if a > b:
        a, b = b, a
    d = b - a
    # floor(d * phi) = (d * (1 + sqrt(5))) / 2 的整数部分
    # 用整数精确计算: floor((d + floor(d*sqrt(5))) / 2 + d/2) 等
    import math
    k = (d * (1 + math.isqrt(5 * d * d)) ) // (2 * d) if d else 0
    # 直接比较: 必败点满足 a == floor(k*phi), b == a + k
    # 由 d = b - a 得 k = floor(d*phi)
    k = (d + math.isqrt(5 * d * d)) // 2
    return a == k and b == a + d and (b - a) == _beatty_gap(a)

def _beatty_gap(a):
    return a
