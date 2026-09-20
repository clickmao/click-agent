LIM = 30

def _lose_table():
    lose = set()
    used = set()
    for i in range(LIM + 1):
        if i in used:
            continue
        j = i + 1
        while j in used:
            j += 1
        lose.add((i, j))
        used.add(i)
        used.add(j)
    return lose

LOSE_PAIRS = _lose_table()

def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    lo, hi = min(a, b), max(a, b)
    if (lo, hi) in LOSE_PAIRS:
        return "LOSE"
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if i == j:
                if (a - i, b - j) in LOSE_PAIRS:
                    return "WIN {0} {1}".format(i, j)
            elif j == 0:
                if (a - i, b) in LOSE_PAIRS:
                    return "WIN {0} {1}".format(i, j)
            else:
                if (a, b - j) in LOSE_PAIRS:
                    return "WIN {0} {1}".format(i, j)
    return "LOSE"
