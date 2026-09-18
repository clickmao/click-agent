import math


LOSE_SET = set()
for n in range(0, 26):
    a = int(math.floor(n * (1 + math.sqrt(5)) / 2))
    b = a + n
    LOSE_SET.add((a, b))
    LOSE_SET.add((b, a))


def solve(text: str) -> str:
    lines = text.split('\n')
    a, b = map(int, lines[0].split())
    if (a, b) in LOSE_SET:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if (a - i, b - j) in LOSE_SET:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
