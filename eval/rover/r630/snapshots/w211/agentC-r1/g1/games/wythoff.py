"""Wythoff's game: losing positions and lexicographically smallest winning move."""


def _is_win(p, q, memo):
    key = (p, q)
    if key in memo:
        return memo[key]
    res = False
    for i in range(1, p + 1):
        if not _is_win(p - i, q, memo):
            res = True
            break
    if not res:
        for j in range(1, q + 1):
            if not _is_win(p, q - j, memo):
                res = True
                break
    if not res:
        t = min(p, q)
        for d in range(1, t + 1):
            if not _is_win(p - d, q - d, memo):
                res = True
                break
    memo[key] = res
    return res


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    memo = {}
    if not _is_win(a, b, memo):
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if not _is_win(a - i, b - j, memo):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return "LOSE"
    return "WIN " + str(best[0]) + " " + str(best[1])
