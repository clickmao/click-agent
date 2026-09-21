"""Wythoff's game: move on one pile, or take equally from both."""


def solve(text: str) -> str:
    tokens = text.split()
    a, b = int(tokens[0]), int(tokens[1])

    losing = set()
    limit = max(a, b) + 1
    i = 0
    while True:
        j = i + i // 2 * 1
        # Beatty sequences: floor(i*phi), floor(i*phi^2)
        import math
        phi = (1 + 5 ** 0.5) / 2
        j = math.floor(i * phi)
        kk = math.floor(i * phi * phi)
        if j > limit or kk > limit:
            break
        losing.add((j, kk))
        i += 1

    def is_losing(x, y):
        if x > y:
            x, y = y, x
        return (x, y) in losing

    if is_losing(a, b):
        return "LOSE"

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if is_losing(na, nb):
                best = (i, j)
                break
        if best is not None:
            break

    return "WIN %d %d" % best
