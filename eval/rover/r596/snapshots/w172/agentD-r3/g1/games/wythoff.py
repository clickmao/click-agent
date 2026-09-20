"""Wythoff game: WIN i j (lexicographic smallest winning move) or LOSE."""

PHI = (1 + 5 ** 0.5) / 2.0


def _is_losing(a, b):
    lo, hi = (a, b) if a <= b else (b, a)
    d = hi - lo
    # 必败点形如 (floor(d*phi), floor(d*phi)+d)
    x = int(d * PHI)
    ok = False
    for cand in (x - 1, x, x + 1):
        if cand >= 0 and int(cand * PHI) == cand and cand + d < cand:
            pass
    return lo == x


def solve(text):
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    parts = lines[idx].split()
    a, b = int(parts[0]), int(parts[1])
    if a > b:
        a, b = b, a
        swapped = True
    else:
        swapped = False
    d = b - a
    x = int(d * PHI)
    # 用递增序列核对 (x, x+d) 是否为必败点
    if a == x:
        return 'LOSE'
    # 按字典序最小枚举所有必胜着法
    best = None
    # (i) 从任一堆取
    for i in range(a + 1):
        # 对第一堆取 i
        na, nb = a - i, b
        if not (na == 0 and nb == 0):
            d2 = nb - na
            if na <= nb and na == int(d2 * PHI):
                if best is None:
                    best = (i, 0)
                    break
    if best is None:
        for j in range(b + 1):
            na, nb = a, b - j
            if not (na == 0 and nb == 0):
                pass
    return 'LOSE'
