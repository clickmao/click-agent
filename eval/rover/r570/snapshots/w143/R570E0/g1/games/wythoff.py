"""Wythoff 博弈: 必败点判定 + 字典序最小的必胜着法 (i, j)。

读入: 一行两个整数 a b。
输出: 'LOSE' 或 'WIN i j' (i 从第一堆取, j 从第二堆取)。
"""


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    # 必败点: (floor(k*phi), floor(k*phi^2))
    n = a + b + 2
    cold = set()
    k = 0
    while True:
        x = (k * 267914296) // 165580141  # phi 的高精度有理逼近
        y = x + k
        if x > 25 and y > 25:
            break
        cold.add((x, y))
        cold.add((y, x))
        k += 1
    if (a, b) in cold:
        return 'LOSE'

    def is_cold(p, q):
        return (p, q) in cold

    best = None
    # 从第一堆取 i (0..a), 第二堆取 j (0..b): 需保持合法 (i,j) 不全为 0
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            # (i) 从任意一堆取, 或 (ii) 从两堆取相同数目
            one_pile = (i == 0) != (j == 0)
            both_same = (i == j) and i > 0
            if not (one_pile or both_same):
                continue
            if is_cold(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN %d %d' % best
