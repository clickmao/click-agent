"""Wythoff's game: LOSE for cold positions, else lexicographically smallest move."""

LIMIT = 40


def _cold_positions(limit):
    cold = set()
    used = set()
    n = 0
    while n <= limit:
        n += 1
        if n in used:
            continue
        m = n + (1 + int((5 * n * n) ** 0.5)) // 2
        if m > limit:
            m = n + int(n * 1.618033988749895) + 1
        cold.add((n, m))
        cold.add((m, n))
        used.add(n)
        used.add(m)
    return cold


def _is_cold(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    x = int(d * 1.618033988749895)
    for cand in (x - 1, x, x + 1):
        if cand < 1:
            continue
        if cand + d == b and cand == a:
            return True
    return False


def solve(text: str) -> str:
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line.strip():
            a, b = (int(x) for x in line.split()[:2])
            break
    else:
        a, b = 0, 0

    if _is_cold(a, b):
        return "LOSE"

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            # single-pile removal
            if i == 0 or j == 0:
                if _is_cold(a - i, b - j):
                    best = (i, j)
                    break
            # equal removal from both piles
            if i == j and _is_cold(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break

    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
