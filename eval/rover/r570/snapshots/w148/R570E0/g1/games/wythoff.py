"""Wythoff game: report a losing position or the lexicographically smallest winning move."""


def _is_losing(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    x = (5 ** 0.5 + 1) / 2.0 * d
    ax = int(x)
    for cand in range(max(0, ax - 3), ax + 4):
        if cand == a and cand + d == b:
            return True
    return False


def solve(text):
    nums = [int(t) for t in text.split()]
    a, b = nums[0], nums[1]
    if _is_losing(a, b):
        return "LOSE"
    cands = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != j and i != 0 and j != 0:
                continue
            na, nb = a - i, b - j
            if _is_losing(na, nb):
                cands.append((i, j))
    cands.sort()
    i, j = cands[0]
    return "WIN %d %d" % (i, j)
