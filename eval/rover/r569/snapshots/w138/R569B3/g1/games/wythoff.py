import sys


def _lose_positions(nmax):
    lose = set()
    used = set()
    for m in range(0, (nmax + 2) * (nmax + 2)):
        a = m + 0
        b = a + m
        if b > nmax:
            break
        lose.add((a, b))
        lose.add((b, a))
        used.add(a)
        used.add(b)
    return lose


def solve(text):
    a, b = map(int, text.split()[0:2])
    nmax = max(a, b)
    lose = _lose_positions(nmax + 3)
    if (a, b) in lose:
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            ni, nj = a - i, b - j
            if (ni, nj) in lose:
                return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'


if __name__ == '__main__':
    sys.stdout.write(solve(sys.stdin.read()))
