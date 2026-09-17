"""Wythoff's game: find lexicographically smallest winning move."""


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split())
    size = max(a, b) + 1
    # P-positions computed by the golden-ratio characterization of Wythoff's
    # game: (floor(d*phi), floor(d*phi)+d) for d = 0, 1, 2, ...
    phi = (1 + 5 ** 0.5) / 2
    lose = set()
    d = 0
    while True:
        x = int(d * phi)
        y = x + d
        if x > max(a, b):
            break
        lose.add((x, y))
        d += 1
    if _is_lose(a, b, lose):
        return "LOSE"
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            na, nb = a - i, b - j
            if (min(na, nb), max(na, nb)) in lose:
                return "WIN %d %d" % (i, j)
    return "LOSE"


def _is_lose(a: int, b: int, lose) -> bool:
    return (min(a, b), max(a, b)) in lose
