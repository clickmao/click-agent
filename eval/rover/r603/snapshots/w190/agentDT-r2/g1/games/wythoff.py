"""Wythoff 博弈: WIN i j / LOSE（字典序最小必胜着法）。

先手必败点恰为 Wythoff 对 (floor(r*phi), floor(r*phi)+r), r>=0;
等价可判据: 设 i=min(a,b), j=max(a,b), r=j-i, 则必败 <=> i == floor(r*phi)。
必胜着法: 枚举所有合法着法 (i,j)（i,j>=0 且不同时为 0; i,j 均取正时必须 i==j 才合法,
即同时从两堆取相同数目），取字典序最小者。
"""


def _loss(a: int, b: int) -> bool:
    i, j = (a, b) if a <= b else (b, a)
    r = j - i
    phi = (1 + 5 ** 0.5) / 2.0
    bi = int(r * phi)
    for cand in (bi - 1, bi, bi + 1):
        if cand >= 0 and cand == i:
            return True
    return False


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    a, b = (int(x) for x in lines[idx].split()[:2])

    if _loss(a, b):
        return 'LOSE'

    best = None
    candidates = []
    for i in range(0, a + 1):
        candidates.append((i, 0))
    for j in range(0, b + 1):
        candidates.append((0, j))
    d = min(a, b)
    for t in range(1, d + 1):
        candidates.append((t, t))
    for (i, j) in candidates:
        if i == 0 and j == 0:
            continue
        if i > a or j > b:
            continue
        if _loss(a - i, b - j):
            if best is None or (i, j) < best:
                best = (i, j)

    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
