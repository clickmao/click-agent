def _cold_positions(limit):
    cold = set()
    for x in range(limit + 1):
        for y in range(x, limit + 1):
            if (x, y) in cold:
                continue
            # (x, y) in normal position iff some move reaches a cold position
            reachable = False
            for i in range(1, x + 1):
                if (x - i, y) in cold or (y, x - i) in cold:
                    reachable = True
                    break
            if not reachable:
                for j in range(1, y + 1):
                    if (x, y - j) in cold or (y - j, x) in cold:
                        reachable = True
                        break
            if not reachable:
                t = min(x, y)
                for d in range(1, t + 1):
                    if (x - d, y - d) in cold:
                        reachable = True
                        break
            if not reachable:
                cold.add((x, y))
    return cold


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    cold = _cold_positions(max(a, b))
    if (min(a, b), max(a, b)) in cold:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            p, q = a - i, b - j
            if (min(p, q), max(p, q)) in cold:
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN %d %d' % best
