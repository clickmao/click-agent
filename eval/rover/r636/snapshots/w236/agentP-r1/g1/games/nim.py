def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0])
    heaps = list(map(int, lines[1].split()))[:m]

    x = 0
    for a in heaps:
        x ^= a

    if x == 0:
        return 'LOSE'

    for idx, a in enumerate(heaps, 1):
        target = a ^ x
        if target < a:
            return 'WIN %d %d' % (idx, a - target)
    return 'LOSE'
