def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])

    losing = set()
    for i in range(0, 26):
        for j in range(0, 26):
            if i == 0 and j == 0:
                continue
            if (i - 1, j) in losing:
                continue
            if (i, j - 1) in losing:
                continue
            if i > 0 and j > 0 and (i - 1, j - 1) in losing:
                continue
            losing.add((i, j))

    if (a, b) in losing:
        return "LOSE"

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (a - i, b - j) in losing:
                return "WIN " + str(i) + " " + str(j)
    return "LOSE"
