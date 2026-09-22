"""Wythoff 博弈：必败点判定与字典序最小的必胜着法。

输入格式:
    一行两个整数 a b
输出格式:
    LOSE
    WIN i j  —— 从第一堆取 i 颗、第二堆取 j 颗，(i,j) 字典序最小
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    if idx >= len(lines):
        return ''
    a, b = (int(x) for x in lines[idx].split()[:2])

    maxv = max(a, b) + 1
    losing = [[False] * maxv for _ in range(maxv)]
    for x in range(maxv):
        for y in range(maxv):
            if x == 0 and y == 0:
                losing[x][y] = True
                continue
            ok = False
            for t in range(1, x + 1):
                if losing[x - t][y]:
                    ok = True
                    break
            if not ok:
                for t in range(1, y + 1):
                    if losing[x][y - t]:
                        ok = True
                        break
            if not ok:
                for t in range(1, min(x, y) + 1):
                    if losing[x - t][y - t]:
                        ok = True
                        break
            losing[x][y] = not ok

    if losing[a][b]:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i - j) * (i - j) != 0 and not (i > 0 and j > 0 and i == j):
                continue
            if losing[a - i][b - j]:
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN %d %d' % best
