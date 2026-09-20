"""Wythoff game: WIN i j / LOSE with lexicographically smallest winning move."""

PHI = (1 + 5 ** 0.5) / 2


def losing_pairs(limit):
    """Set of (a, b) with a < b that are P-positions (cold) with b <= limit."""
    pairs = set()
    used = set()
    n = 0
    while True:
        a = int(n * PHI) + n if False else int(n * PHI)
        # standard: a_n = floor(n*phi), b_n = floor(n*phi^2) = a_n + n
        a = int(n * PHI)
        b = a + n
        if a > limit and b > limit:
            break
        if a > limit and n > 0:
            break
        pairs.add((a, b))
        used.add(a)
        used.add(b)
        n += 1
        if n > 200:
            break
    return pairs, used


def p_positions(limit):
    """Brute-force P-positions up to limit using mex construction."""
    pairs = []
    used = set()
    n = 0
    while True:
        a = 0
        while a in used:
            a += 1
        b = a + n
        if a > limit and b > limit:
            break
        if a > limit:
            break
        pairs.append((a, b))
        used.add(a)
        used.add(b)
        n += 1
        if n > 100:
            break
    return pairs


def is_p(a, b):
    for (x, y) in p_positions(25):
        if (x == a and y == b) or (x == b and y == a):
            return True
    return False


def solve(text: str) -> str:
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    a, b = map(int, lines[0].split()[:2])
    if is_p(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if is_p(na, nb):
                best = (i, j)
                return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
