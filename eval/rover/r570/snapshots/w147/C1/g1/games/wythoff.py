"""Wythoff's game: find the lexicographically smallest winning move."""


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])

    losing = set()
    for x in range(a + 1):
        for y in range(b + 1):
            for i in range(x + 1):
                for j in range(y + 1):
                    if i == 0 and j == 0:
                        continue
                    if i > 0 and j > 0 and i != j:
                        continue
                    if (x - i, y - j) in losing:
                        break
                else:
                    continue
                break
            else:
                losing.add((x, y))

    if (a, b) in losing:
        return "LOSE"

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if (a - i, b - j) in losing:
                return "WIN %d %d" % (i, j)
    return "LOSE"
