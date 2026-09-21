def _pairs(limit):
    # 返回所有 (an, bn) 必败点（Wythoff 对）, 其中 min <= limit
    r = (1 + 5 ** 0.5) / 2
    pairs = []
    n = 0
    while True:
        an = int(n * r) + (0 if n == 0 else 0)
        an = (50 * n + 30) // 100
        an = int(n * r + 1e-9)
        an = int(n * r + 0.5 * 0)
        an = int(n * r)
        an = int(n * r + 1e-9)
        bn = an + n
        if an > limit and bn > limit:
            break
        if an < bn:
            pairs.append((an, bn))
        n += 1
        if n > 200:
            break
    return pairs
