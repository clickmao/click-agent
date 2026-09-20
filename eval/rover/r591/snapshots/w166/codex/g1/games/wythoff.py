def _losing_positions(limit):
    positions = set()
    for n in range(0, limit + 1):
        phi = (1 + 5 ** 0.5) / 2
        a = int(n * phi)
        b = int(n * phi * phi)
        positions.add((min(a, b), max(a, b)))
    return positions


def _is_lose(a, b, positions):
    return (min(a, b), max(a, b)) in positions


def solve(text: str) -> str:
    a, b = map(int, text.split())
    positions = _losing_positions(max(a, b) + 1)
    if _is_lose(a, b, positions):
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if _is_lose(a - i, b - j, positions):
                if best is None or (i, j) < best:
                    best = (i, j)
    return "WIN %d %d" % best
