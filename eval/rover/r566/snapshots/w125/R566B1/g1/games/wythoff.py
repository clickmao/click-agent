"""Wythoff game: two piles a b; lose positions are (floor(n*phi), floor(n*phi*phi))."""


def solve(text: str) -> str:
    lines = text.split('\n')
    if len(lines) >= 1 and lines[-1] == '':
        lines = lines[:-1]
    a, b = (int(x) for x in lines[0].split())
    lo, hi = (a, b) if a <= b else (b, a)
    # check whether (lo, hi) is a P-position
    is_p = False
    n = 0
    while True:
        x = int(n * 1.6180339887498949)
        y = x + n
        if y > hi or x > lo:
            break
        if x == lo and y == hi:
            is_p = True
            break
        n += 1
    if is_p:
        return 'LOSE'
    best = None
    # take from first pile only
    for i in range(1, a + 1):
        if (i, 0) < (1, 0) if False else True:
            if is_lose(a - i, b):
                cand = (i, 0)
                if best is None or cand < best:
                    best = cand
    # take from second pile only
    for j in range(1, b + 1):
        if is_lose(a, b - j):
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    # take same from both
    for t in range(1, min(a, b) + 1):
        if is_lose(a - t, b - t):
            cand = (t, t)
            if best is None or cand < best:
                best = cand
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])


def is_lose(a: int, b: int) -> bool:
    lo, hi = (a, b) if a <= b else (b, a)
    if a == 0 and b == 0:
        return True
    n = hi - lo
    if n < 0:
        return False
    x = (n * 1000000 + 618033) // 1000000
    # use exact-ish check via Beatty: lower = floor(n*phi)
    n2 = n
    lower = int(n2 * 1.6180339887498949)
    if lower + n2 != hi or lower != lo:
        return False
    return True
