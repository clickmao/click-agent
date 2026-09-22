def _losing(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    # losing positions: (floor(phi*d), floor(phi*d)+d)
    import math
    phi = (1 + math.sqrt(5)) / 2
    x = int(math.floor(phi * d))
    return a == x


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    a, b = map(int, lines[idx].split())

    if _losing(a, b):
        return 'LOSE'

    candidates = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            # move from single pile
            single = (i == 0 and j > 0) or (j == 0 and i > 0)
            # move from both piles equal
            both_equal = (i == j)
            if not (single or both_equal):
                continue
            na, nb = a - i, b - j
            if na < 0 or nb < 0:
                continue
            if _losing(na, nb):
                candidates.append((i, j))

    if not candidates:
        return 'LOSE'
    candidates.sort()
    i, j = candidates[0]
    return 'WIN ' + str(i) + ' ' + str(j)
