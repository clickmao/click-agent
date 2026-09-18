"""Wythoff's game: report the lexicographically smallest winning move or LOSE."""


def solve(text: str) -> str:
    data = text.split()
    a, b = int(data[0]), int(data[1])

    losing = set()
    # (a, b) is a Wythoff cold position iff {a, b} = {floor(n*phi), floor(n*phi^2)}.
    phi = (1 + 5 ** 0.5) / 2
    n = 0
    while True:
        x = int(n * phi)
        y = int(n * phi * phi)
        if x > max(a, b):
            break
        losing.add((x, y))
        losing.add((y, x))
        n += 1

    if (a, b) in losing:
        return "LOSE"

    # Enumerate moves in lexicographic order of (i, j).
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if (a - i, b - j) in losing:
                return "WIN %d %d" % (i, j)

    return "LOSE"
