"""Wythoff game: check losing position; else lexicographically smallest winning move."""


def _is_losing(a, b):
    lost = set()
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                lost.add((0, 0))
                continue
            islose = False
            if not islose:
                for x in range(i):
                    if (x, j) in lost:
                        islose = True
                        break
            if not islose:
                for y in range(j):
                    if (i, y) in lost:
                        islose = True
                        break
            if not islose:
                d = min(i, j)
                for t in range(1, d + 1):
                    if (i - t, j - t) in lost:
                        islose = True
                        break
            if islose:
                lost.add((i, j))
    return (a, b) in lost


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split())
    if _is_losing(a, b):
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i and j and i != j:
                continue
            if _is_losing(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
