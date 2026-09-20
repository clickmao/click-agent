def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])

    def losing(x, y):
        if x > y:
            x, y = y, x
        d = y - x
        return x == int(d * 1.618033988749895)

    if losing(a, b):
        return "LOSE"
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if losing(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
