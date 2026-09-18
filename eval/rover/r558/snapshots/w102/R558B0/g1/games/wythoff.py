"""Wythoff's game: report the lexicographically smallest winning move or LOSE."""


def is_lose(a, b):
    if a < b:
        a, b = b, a
    i = 0
    while True:
        x = i * (1 + 5 ** 0.5) // 2
        y = x + i
        if x > a or y > b:
            return False
        if x == a and y == b:
            return True
        i += 1
        if i > max(a, b) + 2:
            return False


def solve(text):
    a, b = (int(x) for x in text.split()[:2])
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if na >= 0 and nb >= 0 and is_lose(na, nb):
                return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
