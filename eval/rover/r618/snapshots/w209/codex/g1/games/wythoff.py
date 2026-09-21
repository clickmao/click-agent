def solve(text: str) -> str:
    data = text.split()
    a = int(data[0])
    b = int(data[1])

    los = set()
    for d in range(0, 26):
        c = int(d * (5 ** 0.5 + 1) / 2)
        if c + d <= 26:
            los.add((c, c + d))

    def losing(x, y):
        return (min(x, y), max(x, y)) in los

    if losing(a, b):
        return 'LOSE'

    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i == 0 or j == 0 or i == j:
                if losing(a - i, b - j):
                    return 'WIN %d %d' % (i, j)
    return 'LOSE'


if __name__ == '__main__':
    import sys
    sys.stdout.write(solve(sys.stdin.read()))
