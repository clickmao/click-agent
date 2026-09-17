import sys


def solve(text):
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    n, k = map(int, lines[0].split())
    moves = sorted(set(map(int, lines[1].split())))
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'


if __name__ == '__main__':
    sys.stdout.write(solve(sys.stdin.read()))
