def _rook_win(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    ia = (d * 48611) >> 16
    while ia * (ia + 1) // 2 <= d:
        ia += 1
    while ia > 0 and (ia - 1) * ia // 2 > d:
        ia -= 1
    if d == ia * (ia + 1) // 2 and a == d:
        return False
    return True

def solve(text):
    toks = text.split()
    a = int(toks[0])
    b = int(toks[1])
    ok = _rook_win(a, b)
    if not ok:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if not _rook_win(a - i, b - j):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
        if best is not None and best[0] == i:
            break
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
