"""Wythoff's game: report the lexicographically smallest winning move (i, j)."""


LIMIT = 64

def _cold_table(limit):
    cold = set()
    for x in range(limit + 1):
        for y in range(x, limit + 1):
            if _is_cold(x, y, cold):
                cold.add((x, y))
    return cold


def _is_cold(x, y, cold):
    for (px, py) in cold:
        if x == px or y == py or (x - px) == (y - py) or (y - px) == (x - py):
            return False
    return True


def solve(text: str) -> str:
    line = text.split('\n')[0]
    a, b = (int(x) for x in line.split()[:2])
    cold = _cold_table(LIMIT)
    if (min(a, b), max(a, b)) in cold or (max(a, b), min(a, b)) in cold:
        return 'LOSE'
    best = None
    # (i) remove i from heap1, j from heap2, i>=0, j>=0, i+j>0
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (min(a - i, b - j), max(a - i, b - j)) in cold:
                if best is None or (i, j) < best:
                    best = (i, j)
                break
    if best is None:
        # (ii) remove the same positive amount t from both heaps
        for t in range(1, min(a, b) + 1):
            if (min(a - t, b - t), max(a - t, b - t)) in cold:
                if best is None or (t, t) < best:
                    best = (t, t)
                break
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
