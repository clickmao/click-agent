def solve(text):
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    heaps = list(map(int, lines[1].split()[:m]))
    x = 0
    for a in heaps:
        x ^= a
    if x == 0:
        return 'LOSE'
    for p in range(m):
        r = heaps[p] - (x ^ heaps[p])
        if r > 0:
            return 'WIN %d %d' % (p + 1, r)
    return 'LOSE'
