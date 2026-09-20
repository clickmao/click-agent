import functools


def solve(text):
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    a = list(map(int, lines[1].split()))
    x = functools.reduce(lambda p, q: p ^ q, a, 0)
    if x == 0:
        return 'LOSE'
    for i in range(m):
        t = a[i] ^ x
        if t < a[i]:
            return 'WIN ' + str(i + 1) + ' ' + str(a[i] - t)
    return 'LOSE'
