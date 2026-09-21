"""Wythoff's game: LOSE or lexicographically-minimal WIN i j."""


def _lose_positions(limit: int):
    pairs = set([(0, 0)])
    a, b = 0, 0
    while b <= limit:
        a, b = b + 1, a + b + 2
        pairs.add((a, b))
        pairs.add((b, a))
    return pairs


def solve(text: str) -> str:
    p, q = (int(x) for x in text.split())
    lose = _lose_positions(max(p, q))
    if (p, q) in lose:
        return "LOSE"
    best = None
    for i in range(p + 1):
        for j in range(q + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0 or j == 0 or i == j) and (p - i, q - j) in lose:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return "WIN %d %d" % best
