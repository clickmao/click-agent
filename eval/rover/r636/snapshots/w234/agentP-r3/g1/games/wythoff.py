"""Wythoff 博弈: 返回 "LOSE" 或 "WIN i j"（字典序最小的必胜着法, (i, j) 取自第一/第二堆）。"""


def _lose_pairs(limit: int):
    """返回前若干 Wythoff 必败点，规范化为 (a <= b) 的元组集合。"""
    pairs = set()
    used = set()
    nn = 0
    while len(pairs) < limit:
        if nn in used:
            nn += 1
            continue
        mm = nn + len(pairs) + 1
        used.add(nn)
        used.add(mm)
        pairs.add((nn, mm))
        nn += 1
    return pairs


def _norm(a: int, b: int):
    return (a, b) if a <= b else (b, a)


def solve(text: str) -> str:
    lines = text.split('\n')
    if lines and lines[-1].strip() == '':
        lines.pop()
    a, b = (int(x) for x in lines[0].split())

    lose = _lose_pairs(64)
    if _norm(a, b) in lose:
        return 'LOSE'

    best = None
    # 取法 (i, j) 是第一堆取 i 颗、第二堆取 j 颗；合法取法集合先枚举后筛选。
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if _norm(na, nb) in lose:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return 'WIN %d %d' % best
