def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    if b < a:
        a, b = b, a
    limit = b + 2
    used = set()
    cold = set()
    n = 0
    while len(cold) < limit:
        if n not in used:
            m = n + 1
            while m in used:
                m += 1
            used.add(n)
            used.add(m)
            cold.add((n, m))
        n += 1
    if (a, b) in cold:
        return 'LOSE'
    best = None
    for k in range(b + 1):
        # take k from both piles
        if k > 0 and a - k >= 0:
            t = (min(a - k, b - k), max(a - k, b - k))
            if t in cold:
                cand = (k, k)
                if best is None or cand < best:
                    best = cand
        # take k from pile b only
        if k > 0:
            t = (min(a, b - k), max(a, b - k))
            if t in cold:
                cand = (0, k)
                if best is None or cand < best:
                    best = cand
        # take k from pile a only
        if k > 0 and a - k >= 0:
            t = (min(a - k, b), max(a - k, b))
            if t in cold:
                cand = (k, 0)
                if best is None or cand < best:
                    best = cand
    return 'WIN %d %d' % best
