"""Wythoff 博弈必败点判定。"""


def _is_losing(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    x = (d * (1 + 5 ** 0.5)) / 2.0
    cand = int(x)
    for t in (cand - 2, cand - 1, cand, cand + 1, cand + 2):
        if t >= 0 and d + t == b and t == a:
            return True
    return False


def solve(text):
    tok = text.split()
    a, b = int(tok[0]), int(tok[1])
    if _is_losing(a, b):
        return 'LOSE'
    cands = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j == 0) or (i == 0 and j > 0) or (i == j):
                if _is_losing(a - i, b - j):
                    cands.append((i, j))
    cands.sort()
    i, j = cands[0]
    return 'WIN ' + str(i) + ' ' + str(j)
