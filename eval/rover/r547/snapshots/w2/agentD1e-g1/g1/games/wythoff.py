"""Wythoff game: lose-point test and lexicographically smallest winning move."""


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    if a > b:
        a, b = b, a
    # Cold (P) positions are (floor(n*phi), floor(n*phi^2)).
    phi = (1 + 5 ** 0.5) / 2
    n = int(b - a) if False else None
    n = b - a
    if n >= 0:
        x = int(n * phi)
        if x == a and x + n == b:
            return "LOSE"
    # brute-force search for the lexicographically smallest winning move
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if i > 0 and j == 0 and i > a:
                continue
            if j > 0 and i == 0 and j > b:
                continue
            na, nb = a - i, b - j
            if na < 0 or nb < 0:
                continue
            x, y = (na, nb) if na <= nb else (nb, na)
            d = y - x
            t = int(d * phi)
            if t == x and t + d == y:
                return "WIN %d %d" % (i, j)
    return "LOSE"
