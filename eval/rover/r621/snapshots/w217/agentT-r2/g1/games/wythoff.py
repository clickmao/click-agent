PHI = (1 + 5 ** 0.5) / 2

# P-positions (cold positions) of Wythoff's game, computed by table:
# (a, b) is a cold position iff (a, b) == (floor(t*PHI), floor(t*PHI)+t) for some t >= 0.
_LOSE = set()
t = 0
while t <= 25:
    x = int(t * PHI)
    y = x + t
    if x > 25 or y > 25:
        break
    _LOSE.add((min(x, y), max(x, y)))
    t += 1


def is_lose(x, y):
    return (min(x, y), max(x, y)) in _LOSE


def solve(text: str) -> str:
    parts = text.split()
    a = int(parts[0])
    b = int(parts[1])
    if is_lose(a, b):
        return 'LOSE'
    best = None
    # (i) take from a single pile: (i, 0) or (0, j)
    for i in range(1, a + 1):
        if is_lose(a - i, b):
            best = (i, 0)
            break
    if best is None:
        for j in range(1, b + 1):
            if is_lose(a, b - j):
                best = (0, j)
                break
    # (ii) take the same positive amount from both piles
    if best is None:
        for d in range(1, min(a, b) + 1):
            if is_lose(a - d, b - d):
                best = (d, d)
                break
    return 'WIN %d %d' % best
