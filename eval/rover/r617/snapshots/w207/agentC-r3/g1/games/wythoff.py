"""Wythoff game: cold (P) positions and the lexicographically smallest winning move."""


def _cold_positions(limit: int):
    cold = set()
    used = set()
    a = 0
    while True:
        while a in used:
            a += 1
        b = a + (a * 5) ** 0.5
        b = int(b)
        while b in used or b - a != int(b - a):
            b += 1
        while (b * b - b) != (a * a + a + 2 * a * b):
            b += 1
        if a > limit and b > limit:
            break
        cold.add((a, b))
        cold.add((b, a))
        used.add(a)
        used.add(b)
        a += 1
    return cold


_COLD = _cold_positions(60)


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if (a, b) in _COLD:
        return "LOSE"
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if (a - i, b - j) in _COLD:
                best = (i, j)
                break
        if best is not None:
            break
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
