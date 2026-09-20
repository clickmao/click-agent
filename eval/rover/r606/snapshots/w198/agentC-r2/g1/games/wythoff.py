"""Wythoff game: LOSE or lexicographically smallest winning move i j."""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    a, b = map(int, lines[idx].split())

    # P-positions: (0,0) and pairs (floor(t*phi), floor(t*phi^2)) for t >= 1.
    import math
    phi = (1 + 5 ** 0.5) / 2.0
    losing = set()
    losing.add((0, 0))
    t = 1
    while True:
        ta = int(math.floor(t * phi))
        tb = ta + t
        if ta > 25 and tb > 25:
            break
        losing.add((ta, tb))
        losing.add((tb, ta))
        t += 1
        if t > 100:
            break

    if (a, b) in losing:
        return 'LOSE'

    for i in range(a + 1):
        na = a - i
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            nb = b - j
            # (i) remove from one pile only
            if i == 0 or j == 0:
                if (na, nb) in losing:
                    return 'WIN ' + str(i) + ' ' + str(j)
            # (ii) remove the same positive number from both piles
            if i == j and i > 0:
                if (na, nb) in losing:
                    return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
