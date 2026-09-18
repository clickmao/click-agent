def _losing_positions(limit: int):
    """Return the set of P-positions (p, q), p <= q, with q <= limit."""
    # Wythoff P-positions are (floor(n*phi), floor(n*phi^2)); generate them
    # directly from the definition with exact integer arithmetic.
    phi = (1 + 5 ** 0.5) / 2
    pairs = set()
    n = 0
    while True:
        p = int(n * phi)
        q = p + n
        if q > limit:
            break
        pairs.add((p, q))
        n += 1
    return pairs


_PAIRS = _losing_positions(25)


def _losing(p: int, q: int) -> bool:
    if p > q:
        p, q = q, p
    return (p, q) in _PAIRS


def solve(text: str) -> str:
    a, b = map(int, text.split())

    if _losing(a, b):
        return "LOSE"
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if _losing(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
