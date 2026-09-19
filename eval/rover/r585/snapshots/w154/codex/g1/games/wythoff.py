"""Wythoff's game: take from one heap, or equal amounts from both."""


def solve(text: str) -> str:
    tokens = text.split()
    a, b = int(tokens[0]), int(tokens[1])

    # losing positions: (floor(n*phi), floor(n*phi^2)) up to the max needed
    phi = (1 + 5 ** 0.5) / 2
    limit = 200
    losing = set()
    for n in range(1, limit):
        x = int(n * phi)
        y = int(n * phi * phi)
        if x > 60 and y > 60:
            break
        losing.add((x, y))

    def is_losing(p: int, q: int) -> bool:
        lo, hi = (p, q) if p <= q else (q, p)
        return (lo, hi) in losing

    if is_losing(a, b):
        return "LOSE"

    # all legal moves: (i, j) taken from heap1 and heap2
    candidates = []
    for i in range(0, a + 1):
        if i > 0:
            candidates.append((i, 0))
        j = i
        if 0 < j <= b:
            candidates.append((i, j))
    # taking from heap1 and heap2 requires i == j when both nonzero;
    # moves taking only from heap2:
    for j in range(1, b + 1):
        candidates.append((0, j))

    for (i, j) in sorted(candidates):
        if (i == 0 and j == 0):
            continue
        if is_losing(a - i, b - j):
            return "WIN %d %d" % (i, j)

    return "LOSE"
