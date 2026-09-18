import sys


def solve(text: str) -> str:
    lines = text.split('\n')
    i = 0
    while i < len(lines) and lines[i].strip() == '':
        i += 1
    a, b = map(int, lines[i].split())
    s = set()
    x, y = 0, 0
    while x <= 25 and y <= 25:
        s.add((x, y))
        x += 1
        y += 2
    lo = min(a, b)
    hi = max(a, b)
    if lo == a and hi == b and (a, b) in s:
        return 'LOSE'
    if lo == b and hi == a and (a, b) in s:
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i == j and i > 0:
                continue
            if i > 0 and j > 0:
                continue
            na = a - i
            nb = b - j
            l2 = min(na, nb)
            h2 = max(na, nb)
            if (l2, h2) in s:
                return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
