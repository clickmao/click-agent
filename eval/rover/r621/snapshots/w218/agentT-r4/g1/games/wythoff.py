def _is_lose(a, b):
    if a > b:
        a, b = b, a
    n = (3 - 5 ** 0.5) / 2 * a
    for cand in (int(n), int(n) + 1, int(n) + 2):
        if cand < 0:
            continue
        w = int(cand * (5 ** 0.5 + 1) / 2) + cand
        if w == a and cand + w == b:
            return True
    return False


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    if _is_lose(a, b):
        return 'LOSE'
    for i in range(a + 1):
        j = i
        na, nb = a - i, b - j
        if not (i == 0 and j == 0) and _is_lose(na, nb):
            return 'WIN ' + str(i) + ' ' + str(j)
    for i in range(1, a + 1):
        if _is_lose(a - i, b):
            return 'WIN ' + str(i) + ' 0'
    for j in range(1, b + 1):
        if _is_lose(a, b - j):
            return 'WIN 0 ' + str(j)
    return 'LOSE'
