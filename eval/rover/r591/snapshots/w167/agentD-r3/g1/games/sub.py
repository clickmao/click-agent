import sys


def _read(text):
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    return lines


def solve(text: str) -> str:
    lines = _read(text)
    if not lines:
        return ''
    n, k = map(int, lines[0].split())
    steps = sorted(set(map(int, lines[1].split()[:k])))
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'


def main():
    data = sys.stdin.read()
    sys.stdout.write(solve(data))
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
