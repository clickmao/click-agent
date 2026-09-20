def _losing_pairs(limit: int):
    pairs = []
    for x in range(limit + 1):
        for y in range(x, limit + 1):
            ok = True
            for (p, q) in pairs:
                if p == x or q == y or (x - p) == (y - q):
                    ok = False
                    break
            if ok:
                pairs.append((x, y))
    return pairs


def _is_losing(a: int, b: int) -> bool:
    x, y = (a, b) if a <= b else (b, a)
    pairs = _losing_pairs(max(a, b))
    return (x, y) in pairs


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    pairs = _losing_pairs(max(a, b))
    if tuple(sorted((a, b))) in pairs:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if tuple(sorted((a - i, b - j))) in pairs:
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
