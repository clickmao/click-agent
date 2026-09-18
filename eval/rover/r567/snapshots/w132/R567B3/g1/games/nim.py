def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    heaps = list(map(int, lines[1].split()))[:m]
    x = 0
    for a in heaps:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i, a in enumerate(heaps):
        target = a ^ x
        if target < a:
            return 'WIN %d %d' % (i + 1, a - target)
    return 'LOSE'
