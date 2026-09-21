"""Wythoff 博弈: 必败点判定, 否则输出字典序最小的必胜着法。

约定: text 为该游戏的完整 stdin 文本; 返回应当写出的 stdout 文本, 末尾不带换行。
"""


def _lose_set(limit: int):
    """返回 (x, y) 形式的冷态点集合, x <= y, 两堆均不超过 limit。"""
    lose = set()
    for a in range(limit + 1):
        for b in range(a, limit + 1):
            wins = False
            for i in range(0, a + 1):
                for j in range(0, b + 1):
                    if i == 0 and j == 0:
                        continue
                    if (i == 0 or j == 0) or i == j:
                        na, nb = a - i, b - j
                        if (min(na, nb), max(na, nb)) in lose:
                            wins = True
                            break
                if wins:
                    break
            if not wins:
                lose.add((a, b))
    return lose


def solve(text: str) -> str:
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    if not lines:
        return ''
    a, b = (int(x) for x in lines[0].split())
    limit = max(a, b)
    lose = _lose_set(limit)
    if (min(a, b), max(a, b)) in lose:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            na, nb = a - i, b - j
            if (min(na, nb), max(na, nb)) in lose:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return 'WIN %d %d' % best
