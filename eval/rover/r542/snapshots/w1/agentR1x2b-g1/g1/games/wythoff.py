"""Wythoff game: winning move with lexicographically smallest (i, j)."""


def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])

    def losing(x, y):
        if x > y:
            x, y = y, x
        ai = int((y - x) * 1.6180339887498949)
        for cand in (ai, ai + 1):
            if cand >= 0 and (cand, cand + (y - x)) == (x, y):
                return True
        return False

    if losing(a, b):
        return 'LOSE'

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if losing(a - i, b - j):
                return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
