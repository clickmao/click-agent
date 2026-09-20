import sys


def _read(text):
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    return lines


MAXN = 60


def _cold_table():
    cold = set()
    a, b = 0, 0
    while a < MAXN:
        cold.add((a, b))
        a, b = b, a + 1
    return cold


def _beatty():
    cold = set()
    n = 0
    while True:
        import math
        a = int(math.floor(n * (1 + 5 ** 0.5) / 2))
        b = a + n
        if a >= MAXN or b >= MAXN:
            break
        cold.add((a, b))
        n += 1
    return cold


COLD = set()
for _n in range(0, MAXN):
    _a = (_n * (1 + 5 ** 0.5) / 2)
    _a = int(_a // 1)
    _b = _a + _n
    COLD.add((_a, _b))


def _is_cold(a, b):
    if a > b:
        a, b = b, a
    return (a, b) in COLD


def solve(text: str) -> str:
    lines = _read(text)
    if not lines:
        return ''
    parts = lines[0].split()
    a, b = int(parts[0]), int(parts[1])
    if _is_cold(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if _is_cold(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best


def main():
    data = sys.stdin.read()
    sys.stdout.write(solve(data))
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
