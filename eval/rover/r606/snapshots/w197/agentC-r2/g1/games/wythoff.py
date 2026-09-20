"""Wythoff game: lose if only pile move to no-pile could help; else lexicographically smallest winning move."""


def _lose(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    phi = (1 + 5 ** 0.5) / 2.0
    return a == int(d * phi)


def solve(text):
    a, b = map(int, text.split()[:2])
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            # single-pile move
            if i > 0 and j == 0 or i == 0 and j > 0:
                pass
            # both-pile same amount
            if i == j and i > 0:
                pass
            if (i > 0 and j == 0) or (i == 0 and j > 0) or (i == j and i > 0):
                if _lose(a - i, b - j):
                    return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
