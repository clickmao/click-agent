def solve(text):
    a, b = map(int, text.split())

    def losing(x, y):
        if x > y:
            x, y = y, x
        return x == (y - x) * (1 + 5 ** 0.5) // 2

    if losing(a, b):
        return "LOSE"

    moves = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i == 0 or j == 0 or i == j:
                moves.append((i, j))
    moves.sort()
    for i, j in moves:
        if losing(a - i, b - j):
            return "WIN %d %d" % (i, j)
    return "LOSE"
