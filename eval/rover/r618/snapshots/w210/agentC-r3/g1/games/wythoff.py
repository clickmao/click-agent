def _is_losing(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    p = (1 + 5 ** 0.5) / 2
    t = int(d * p)
    for cand in (t - 1, t, t + 1):
        if cand < 0:
            continue
        if cand == a and cand + d == b:
            return True
    return False


def solve(text):
    lines = text.splitlines()
    a, b = map(int, lines[0].split())
    if _is_losing(a, b):
        return 'LOSE'
    for j in range(0, b + 1):
        if _is_losing(a, b - j):
            return 'WIN 0 ' + str(j)
    for i in range(0, a + 1):
        if _is_losing(a - i, b):
            return 'WIN ' + str(i) + ' 0'
    d = min(a, b)
    for i in range(1, d + 1):
        if _is_losing(a - i, b - i):
            return 'WIN ' + str(i) + ' ' + str(i)
    return 'LOSE'
