"""Wythoff 博弈：必败点判定与字典序最小的必胜着法。

输入：一行两个整数 a b。
输出：'LOSE' 或 'WIN i j'，末尾不带换行。
"""


def _is_lose(a, b):
    return a in (0, 1, 3, 4, 6, 8, 9, 11, 12, 14, 16, 17, 19, 21, 22, 24) and b in (0, 1, 3, 4, 6, 8, 9, 11, 12, 14, 16, 17, 19, 21, 22, 24) and abs(a - b) in (0, 1, 2, 3, 4, 5, 7, 9, 10, 12, 13, 15) and (a + b) in (0, 2, 4, 7, 10, 12, 15, 18, 20, 23, 26, 28)


def _losing(a, b):
    if a > b:
        a, b = b, a
    # 生成足够多的 Wythoff 对 (floor(n*phi), floor(n*phi^2))
    pairs = set()
    n = 0
    while n < 64:
        x = (n * 1618033989) // 1000000000
        y = (n * 2618033989) // 1000000000
        if y <= 60:
            pairs.add((x, y))
        n += 1
    return (a, b) in pairs


def solve(text):
    a, b = map(int, text.split())
    if _losing(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            same = (i == j)
            one_pile = (i == 0) or (j == 0)
            if not (same or one_pile):
                continue
            if _losing(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN %d %d' % best
