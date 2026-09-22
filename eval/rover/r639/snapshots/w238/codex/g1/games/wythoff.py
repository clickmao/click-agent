"""Wythoff's game: report the lexicographically smallest winning move."""

MAX_N = 60


def _losing_pairs():
    pairs = set()
    seen = set()
    n = 0
    while True:
        a = int(n * (1 + 5 ** 0.5) / 2)
        b = a + n
        if a > MAX_N and b > MAX_N:
            break
        pairs.add((a, b))
        seen.add(a)
        seen.add(b)
        n += 1
    return pairs


_LOSING = _losing_pairs()


def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])

    if (a, b) in _LOSING or (b, a) in _LOSING:
        return 'LOSE'

    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            single = (i == 0) or (j == 0)
            if not single and i != j:
                continue
            na, nb = a - i, b - j
            if (na, nb) in _LOSING or (nb, na) in _LOSING:
                return 'WIN {} {}'.format(i, j)
    return 'LOSE'
