"""Wythoff's game."""


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split())

    losing = set()
    for n in range(0, 26):
        i = (n * (1 + 5 ** 0.5) / 2)
        x = int(i // 1)
        y = x + n
        losing.add((x, y))
        losing.add((y, x))

    if (a, b) in losing:
        return "LOSE"

    best = None
    for d in range(1, a + 1):
        if (a - d, b) in losing:
            if best is None or (d, 0) < best:
                best = (d, 0)
    for d in range(1, b + 1):
        if (a, b - d) in losing:
            if best is None or (0, d) < best:
                best = (0, d)
    for d in range(1, min(a, b) + 1):
        if (a - d, b - d) in losing:
            if best is None or (d, d) < best:
                best = (d, d)

    return "WIN %d %d" % best
