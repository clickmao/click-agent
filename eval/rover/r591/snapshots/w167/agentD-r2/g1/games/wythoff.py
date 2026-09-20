"""Wythoff game: two piles a b; output LOSE or lexicographically smallest winning move."""


def _lose_pair(s):
    a = (s * (1 + 5 ** 0.5)) / 2.0
    # round down reliably
    a = int(a)
    while int(((a + 1) * (1 + 5 ** 0.5)) / 2.0) <= s:
        a += 1
    while a > 0 and int((a * (1 + 5 ** 0.5)) / 2.0) > s:
        a -= 1
    # adjust to exact floor(s*phi)
    while int((a * (1 + 5 ** 0.5)) / 2.0) < s:
        a += 1
    while a > 0 and int((a * (1 + 5 ** 0.5)) / 2.0) >= s + 1:
        a -= 1
    b = a + s
    lo = min(a, b)
    hi = max(a, b)
    return lo, hi


def _is_lose(a, b):
    if a > b:
        a, b = b, a
    if a == 0 and b == 0:
        return True
    d = b - a
    cand = _lose_pair(d)
    return cand == (a, b)


def solve(text: str) -> str:
    nums = [int(t) for t in text.split()]
    a, b = nums[0], nums[1]
    if _is_lose(a, b):
        return 'LOSE'
    # search moves in lexicographic order (i, j)
    best = None
    limit = max(a, b)
    # option (i): remove from one pile
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if i > 0 and j > 0 and i != j:
                continue
            if _is_lose(na, nb):
                best = (i, j)
                break
        if best is not None:
            break
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
