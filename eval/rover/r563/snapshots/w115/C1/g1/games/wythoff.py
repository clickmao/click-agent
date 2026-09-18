def solve(text: str) -> str:
    data = text.split()
    a, b = int(data[0]), int(data[1])

    def is_losing(x, y):
        if x > y:
            x, y = y, x
        return x == int((y - x) * (1 + 5 ** 0.5) / 2)

    if is_losing(a, b):
        return "LOSE"

    def is_win(x, y):
        if x > y:
            x, y = y, x
        return x == int((y - x) * (1 + 5 ** 0.5) / 2)

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if is_win(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break
    return "WIN %d %d" % best
