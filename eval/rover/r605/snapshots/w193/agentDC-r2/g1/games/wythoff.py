"""Wythoff game: decide win/lose and the lexicographically smallest winning move."""


def solve(text: str) -> str:
    parts = text.split()
    if len(parts) < 2:
        return "LOSE"
    a, b = int(parts[0]), int(parts[1])

    # P-positions (losing for the player to move) of Wythoff: (floor(n*phi), floor(n*phi^2))
    limit = 30
    phi = (1 + 5 ** 0.5) / 2
    losing = set()
    for n in range(0, limit):
        x = int(n * phi)
        y = int(n * phi * phi)
        if x <= 26 and y <= 26:
            losing.add((x, y))
            losing.add((y, x))

    if (a, b) in losing:
        return "LOSE"

    candidates = []
    # (i) take i from first pile only
    for i in range(1, a + 1):
        if (a - i, b) in losing:
            candidates.append((i, 0))
    # (i) take j from second pile only
    for j in range(1, b + 1):
        if (a, b - j) in losing:
            candidates.append((0, j))
    # (ii) take d from both piles
    for d in range(1, min(a, b) + 1):
        if (a - d, b - d) in losing:
            candidates.append((d, d))

    i, j = min(candidates)
    return "WIN " + str(i) + " " + str(j)
