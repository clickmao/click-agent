def _lose(a, b):
    if a > b:
        a, b = b, a
    return a == int((b - a) * (1 + 5 ** 0.5) / 2)


def solve(text: str) -> str:
    data = text.split()
    a, b = int(data[0]), int(data[1])

    if _lose(a, b):
        return 'LOSE'

    best = None
    for i in range(0, a + 1):
        # remove i from pile 1 only
        if _lose(a - i, b):
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
        # remove same i from both piles
        if i <= b and _lose(a - i, b - i):
            cand = (i, i)
            if best is None or cand < best:
                best = cand
    for j in range(0, b + 1):
        # remove j from pile 2 only
        if _lose(a, b - j):
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    return 'WIN %d %d' % best
