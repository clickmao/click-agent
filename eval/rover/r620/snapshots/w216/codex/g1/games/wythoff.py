"""Wythoff's game: remove from one pile, or equal amounts from both."""


def solve(text: str) -> str:
    a, b = (int(v) for v in text.split()[:2])

    losing = set()
    # Cold (P-)positions are (floor(n*phi), floor(n*phi^2)).
    i = 0
    while True:
        x = int(i * 1.6180339887498949)
        y = x + i
        if x > 25 and y > 25:
            break
        losing.add((x, y))
        losing.add((y, x))
        i += 1
        if i > 100:
            break

    if (a, b) in losing:
        return 'LOSE'

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (a - i, b - j) in losing:
                best = (i, j)
                break
        if best is not None:
            break

    return 'WIN %d %d' % best
