def solve(text):
    a, b = map(int, text.split())
    # grundy: losing iff a == floor(b-a)*phi
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i == j) or (i == 0 and j > 0) or (j == 0 and i > 0):
                na, nb = a - i, b - j
                ok = _is_lose(na, nb)
                if ok:
                    return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'


def _is_lose(a, b):
    if a > b:
        a, b = b, a
    return a == int((b - a) * (1 + 5 ** 0.5) / 2)
