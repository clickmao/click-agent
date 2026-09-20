def solve(text: str) -> str:
    data = text.split()
    m = int(data[0])
    heaps = [int(x) for x in data[1:1 + m]]
    x = 0
    for h in heaps:
        x ^= h
    if x == 0:
        return 'LOSE'
    for i, h in enumerate(heaps):
        target = h ^ x
        if target < h:
            return 'WIN %d %d' % (i + 1, h - target)
    return 'LOSE'


if __name__ == '__main__':
    import sys
    sys.stdout.write(solve(sys.stdin.read()))
