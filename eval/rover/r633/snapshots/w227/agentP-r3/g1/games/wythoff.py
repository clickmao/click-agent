"""Wythoff game: losing position or lexicographically smallest winning move.

The P-positions are (floor(n*phi), floor(n*phi**2)) up to swapping, i.e.
(p, q) with p = floor(n*phi), q = p + n.  They are enumerated in ascending
order of p via the exact integer identity p = floor(q*alpha) with
alpha = (sqrt(5)-1)/2, i.e. p = (q*1000000 + 618033) // 1000000 -> use
integer recurrence instead: p_{n} = mex of previous p's, q_n = p_n + n.
"""


def _p_positions(limit: int):
    """All P-positions (p, q) with p <= q and p <= limit."""
    seen = set()
    res = []
    p = 0
    while p <= limit:
        if p in seen:
            p += 1
            continue
        q = p + len(res)
        res.append((p, q))
        seen.add(p)
        seen.add(q)
        p += 1
    return res


def solve(text: str) -> str:
    tokens = text.split()
    a, b = int(tokens[0]), int(tokens[1])
    if a > b:
        a, b = b, a
    limit = b + 1
    losing = set()
    for (p, q) in _p_positions(limit):
        losing.add((p, q))
        losing.add((q, p))
    if (a, b) in losing:
        return 'LOSE'
    cand = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if (a - i, b - j) in losing:
                cand.append((i, j))
    if not cand:
        return 'LOSE'
    best = min(cand)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
