"""Wythoff's game: lexicographically smallest winning move."""


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])

    cold = set()
    for x in range(a + 1):
        for y in range(b + 1):
            if x == 0 and y == 0:
                continue
            is_cold = True
            for i in range(x + 1):
                if (i, y) in cold:
                    is_cold = False
                    break
            if is_cold:
                for j in range(y + 1):
                    if (x, j) in cold:
                        is_cold = False
                        break
            if is_cold:
                for d in range(1, min(x, y) + 1):
                    if (x - d, y - d) in cold:
                        is_cold = False
                        break
            if is_cold:
                cold.add((x, y))

    if (a, b) in cold:
        return 'LOSE'

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if (a - i, b - j) in cold:
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN %d %d' % best
