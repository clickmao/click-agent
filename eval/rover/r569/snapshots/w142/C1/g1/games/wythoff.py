def _losing_positions(limit):
    seen = set()
    losing = set()
    for t in range(0, limit):
        lo = None
        for c in range(0, limit * 2):
            if c not in seen:
                lo = c
                break
        if lo is None:
            break
        hi = lo + t
        seen.add(lo)
        seen.add(hi)
        losing.add((lo, hi))
        losing.add((hi, lo))
    return losing


def solve(text: str) -> str:
    tokens = text.split()
    a, b = int(tokens[0]), int(tokens[1])
    losing = _losing_positions(100)
    if (a, b) in losing:
        return 'LOSE'

    moves = []
    for i in range(1, a + 1):
        moves.append((i, 0))
    for j in range(1, b + 1):
        moves.append((0, j))
    for k in range(1, min(a, b) + 1):
        moves.append((k, k))
    moves.sort()

    for i, j in moves:
        na, nb = a - i, b - j
        if na == 0 and nb == 0:
            return 'WIN %d %d' % (i, j)
        if (na, nb) in losing:
            return 'WIN %d %d' % (i, j)
    return 'LOSE'
