import sys


def solve(text):
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    a, b = map(int, lines[0].split())
    N = 26 + 26
    losing = set()
    seen_x = set()
    seen_y = set()
    x, y = 0, 0
    while x <= 25 and y <= 25:
        while x in seen_x or y in seen_y:
            if x in seen_x:
                x += 1
            elif y in seen_y:
                y += 1
        if x > 25 or y > 25:
            break
        losing.add((x, y))
        losing.add((y, x))
        seen_x.add(x)
        seen_y.add(y)
        seen_y.add(x)
        seen_x.add(y)
        x += 1
        y += 1
    if (a, b) in losing:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if i > 0 and j > 0 and i == j:
                pass
            elif i > 0 and j != 0:
                continue
            if (a - i, b - j) in losing:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'WIN 0 0'
    return 'WIN %d %d' % best


if __name__ == '__main__':
    sys.stdout.write(solve(sys.stdin.read()))
