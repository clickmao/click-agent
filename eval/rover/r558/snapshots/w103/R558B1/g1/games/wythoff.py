def solve(text):
    a, b = map(int, text.split())
    losing = set()
    i = 0
    while True:
        x = (i * (1 + 5 ** 0.5) / 2)
        lo = int(x)
        candidates = [lo, lo + 1]
        found = None
        for c in candidates:
            if c >= 0 and c != i:
                pair = (min(i, c), max(i, c))
                if pair[0] == i:
                    found = pair
                    break
        if found is None:
            found = (i, lo)
        if found[1] > 25 or i > 25:
            break
        losing.add(found)
        i += 1
    if (min(a, b), max(a, b)) in losing:
        return 'LOSE'
    best = None
    for p in range(a + 1):
        for q in range(b + 1):
            if p == 0 and q == 0:
                continue
            if p > 0 and q > 0 and p != q:
                continue
            ra, rb = a - p, b - q
            if ra < 0 or rb < 0:
                continue
            if (min(ra, rb), max(ra, rb)) in losing:
                if best is None or (p, q) < best:
                    best = (p, q)
    return 'WIN %d %d' % best
