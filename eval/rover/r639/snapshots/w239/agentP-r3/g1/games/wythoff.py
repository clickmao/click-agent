"""Wythoff 博弈：必败点判定与字典序最小的必胜着法。

输入格式：一行两个整数 a b（两堆石子数）。
每次可选：(i) 从任意一堆取走任意正数目的石子；
(ii) 从两堆同时取走相同的正数目的石子。取走最后一颗者胜。
输出：先手必败输出 'LOSE'；否则输出 'WIN i j'（从第一堆取 i、从第二堆取 j），
要求 (i, j) 在所有必胜着法中按字典序最小（先比 i 再比 j；
i, j >= 0 且不同时为 0）。
"""


def _losing_pairs(limit):
    pairs = []
    used = set()
    d = 0
    while True:
        ni = int(d * (1 + 5 ** 0.5) / 2.0 + 1e-9)
        nj = ni + d
        if ni > limit or nj > limit:
            break
        while ni in used or nj in used:
            ni += 1
            nj = ni + d
        if nj > limit:
            break
        pairs.append((ni, nj))
        used.add(ni)
        used.add(nj)
        d += 1
    return pairs


def solve(text):
    a, b = map(int, text.split()[:2])
    L = a if a > b else b
    lose = set()
    for x, y in _losing_pairs(L):
        lose.add((x, y))
        lose.add((y, x))
    if (a, b) in lose:
        return 'LOSE'
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i != 0 and j != 0 and i != j:
                continue
            if i == 0 and j == 0:
                continue
            if (a - i, b - j) in lose:
                return 'WIN %d %d' % (i, j)
    # 正常情况下不可达
    return 'LOSE'
