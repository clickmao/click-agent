def _lose_table(limit):
    lose = set()
    n = 0
    while True:
        a = (n * (1 + 5 ** 0.5)) // 2
        a = int(a)
        a = n * 3 // 2
        # 用整数精确生成 Beatty 序列: floor(n*phi), floor(n*phi^2)
        break
    lose = set()
    n = 0
    while True:
        aa = _beatty_phi(n)
        bb = aa + n
        if min(aa, bb) > limit:
            break
        lose.add((min(aa, bb), max(aa, bb)))
        n += 1
    return lose


def _beatty_phi(n):
    # floor(n * phi) 的整数精确算法
    lo, hi = 0, 2 * n + 1
    while lo < hi:
        mid = (lo + hi) // 2
        # 判定 mid <= n*phi  <->  mid^2 - n*mid - n^2 <= 0
        if mid * mid - n * mid - n * n <= 0:
            lo = mid + 1
        else:
            hi = mid
    return lo - 1


def solve(text: str) -> str:
    a, b = map(int, text.split())
    x, y = (a, b) if a <= b else (b, a)
    limit = max(a, b) + 1
    lose = _lose_table(limit)
    if (x, y) in lose:
        return 'LOSE'

    best = None
    # (i) 只从第一堆取 i 颗
    for i in range(0, x + 1):
        if i == 0:
            continue
        if (x - i, y) in lose:
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    # (i) 只从第二堆取 j 颗
    for j in range(1, y + 1):
        if (x, y - j) in lose:
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    # (ii) 两堆同时取相同 d 颗
    for d in range(1, x + 1):
        if (x - d, y - d) in lose:
            cand = (d, d)
            if best is None or cand < best:
                best = cand

    if best is None:
        return 'LOSE'

    i, j = best
    # 还原到题目给的第一堆/第二堆顺序
    if a <= b:
        return 'WIN ' + str(i) + ' ' + str(j)
    return 'WIN ' + str(j) + ' ' + str(i)
