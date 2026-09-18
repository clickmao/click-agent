"""Wythoff game: LOSE or WIN i j (lexicographically smallest move)."""


def _is_lose(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    # Wythoff's cold positions: (floor(n*phi), floor(n*phi^2)).
    n = int(((5 ** 0.5 + 1) / 2) * (b - a))
    for t in (n - 2, n - 1, n, n + 1, n + 2):
        if t >= 0:
            p = (int(t * ((5 ** 0.5 + 1) / 2)), int(t * ((5 ** 0.5 + 1) / 2) ** 2))
            if p == (a, b):
                return True
    return False


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    if _is_lose(a, b):
        return 'LOSE'
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if _is_lose(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
