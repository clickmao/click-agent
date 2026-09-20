def solve(text: str) -> str:
    a, b = (int(x) for x in text.split())
    # losing positions: (floor(k*phi), floor(k*phi^2))
    losing = set()
    for k in range(1, 40):
        x = int(k * (1 + 5 ** 0.5) / 2)
        y = x + k
        if x > 25 or y > 25:
            if x > 25 and y > 25:
                continue
        losing.add((x, y))
        losing.add((y, x))
    if (a, b) in losing:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0 or j == 0 or i == j) and (a - i, b - j) in losing:
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN %d %d' % best


if __name__ == '__main__':
    import sys
    sys.stdout.write(solve(sys.stdin.read()))
