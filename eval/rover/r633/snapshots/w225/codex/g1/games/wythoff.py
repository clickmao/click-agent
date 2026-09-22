def solve(text: str) -> str:
    a, b = map(int, text.split())
    maxn = max(a, b)
    losing = set()
    prev = []
    for n in range(0, maxn + 1):
        cand = n + 1
        while True:
            pair = (cand, cand + n)
            ok = True
            for (x, y) in prev:
                if x == pair[0] or y == pair[1] or (x - y) == (pair[0] - pair[1]):
                    ok = False
                    break
            if ok:
                break
            cand += 1
        prev.append(pair)
        losing.add(pair)
    if (a, b) in losing:
        return 'LOSE'
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            ra, rb = a - i, b - j
            p = (ra, rb) if ra <= rb else (rb, ra)
            if p in losing:
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
