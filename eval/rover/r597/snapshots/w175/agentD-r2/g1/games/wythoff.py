def _cold(a, b):
    '''True if (a, b) is a P-position (cold) of Wythoff's game.'''
    if a > b:
        a, b = b, a
    d = b - a
    return a == int(d * (1 + 5 ** 0.5) / 2)


def solve(text: str) -> str:
    data = text.split()
    a = int(data[0])
    b = int(data[1])
    if _cold(a, b):
        return 'LOSE'
    best = None
    # remove only from pile 1
    for i in range(1, a + 1):
        if _cold(a - i, b):
            if best is None or (i, 0) < best:
                best = (i, 0)
    # remove only from pile 2
    for j in range(1, b + 1):
        if _cold(a, b - j):
            if best is None or (0, j) < best:
                best = (0, j)
    # remove the same amount from both piles
    for t in range(1, min(a, b) + 1):
        if _cold(a - t, b - t):
            if best is None or (t, t) < best:
                best = (t, t)
    return 'WIN %d %d' % best
