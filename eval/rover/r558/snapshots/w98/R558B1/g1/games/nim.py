def solve(text):
    lines = text.splitlines()
    m = int(lines[0])
    heaps = [int(x) for x in lines[1].split()]
    x = 0
    for a in heaps:
        x ^= a
    if x == 0:
        return 'LOSE'
    for p in range(m):
        for r in range(1, heaps[p] + 1):
            nv = heaps[p] - r
            if nv <= heaps[p] and (x ^ heaps[p] ^ nv) == 0:
                return 'WIN %d %d' % (p + 1, r)
    return 'LOSE'
