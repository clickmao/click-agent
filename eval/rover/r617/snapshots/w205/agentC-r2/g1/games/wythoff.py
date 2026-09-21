"""Wythoff 博弈必败点判定与字典序最小的必胜着法。

读入: 一行两个整数 a b (1<=a<=25, 1<=b<=25)。
输出: 必败输出 'LOSE'; 否则输出 'WIN i j' ((i, j) 字典序最小, i,j>=0 不同时为 0)。末尾不带换行。
"""

_MAX = 25


def _build_losing(maxv):
    # 用 P-position 判定: (a,b) 必败 <=> 无合法着法到达必败点
    lose = [[False] * (maxv + 1) for _ in range(maxv + 1)]
    for s in range(2, 2 * maxv + 1):
        for a in range(0, min(s, maxv) + 1):
            b = s - a
            if b < 0 or b > maxv:
                continue
            reachable = False
            # (i) 从任意一堆取正数
            for i in range(1, a + 1):
                if lose[a - i][b]:
                    reachable = True
                    break
            if not reachable:
                for j in range(1, b + 1):
                    if lose[a][b - j]:
                        reachable = True
                        break
            # (ii) 两堆取相同正数
            if not reachable:
                for t in range(1, min(a, b) + 1):
                    if lose[a - t][b - t]:
                        reachable = True
                        break
            lose[a][b] = not reachable
    return lose


_LOSE = _build_losing(_MAX)


def _is_losing(a, b):
    return _LOSE[a][b]


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])

    if _is_losing(a, b):
        return 'LOSE'

    cand = []
    # (i) 从任意一堆取, 或 (ii) 两堆同时取相同数目
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i == 0 or j == 0 or i == j:
                if _is_losing(a - i, b - j):
                    cand.append((i, j))
    cand.sort()
    i, j = cand[0]
    return 'WIN ' + str(i) + ' ' + str(j)
