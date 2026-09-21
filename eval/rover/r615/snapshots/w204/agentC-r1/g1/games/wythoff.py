"""Wythoff game: lose detection and lexicographically smallest winning move."""


def solve(text: str) -> str:
    a, b = map(int, text.split())
    moves = []
    for i in range(0, a + 1):
        moves.append((i, 0))
    for j in range(0, b + 1):
        moves.append((0, j))
    for t in range(1, min(a, b) + 1):
        moves.append((t, t))
    seen = set()
    ordered = []
    for mv in moves:
        if mv in seen:
            continue
        if mv == (0, 0):
            continue
        seen.add(mv)
        ordered.append(mv)
    ordered.sort()
    loses = set()
    for x in range(26):
        for y in range(26):
            if x == 0 and y == 0:
                loses.add((0, 0))
                continue
            losing = True
            for t in range(1, x + 1):
                if (x - t, y) in loses:
                    losing = False
                    break
            if losing:
                for t in range(1, y + 1):
                    if (x, y - t) in loses:
                        losing = False
                        break
            if losing:
                for t in range(1, min(x, y) + 1):
                    if (x - t, y - t) in loses:
                        losing = False
                        break
            if losing:
                loses.add((x, y))
    if (a, b) in loses:
        return "LOSE"
    for i, j in ordered:
        if i <= a and j <= b and (a - i, b - j) in loses:
            return "WIN %d %d" % (i, j)
    return "LOSE"
