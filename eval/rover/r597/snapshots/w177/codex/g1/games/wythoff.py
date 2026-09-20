def _losing(x: int, y: int) -> bool:
    if x > y:
        x, y = y, x
    if x == 0 and y == 0:
        return True
    d = y - x
    return x == int(d * ((5 ** 0.5 + 1) / 2))


def solve(text: str) -> str:
    a, b = map(int, text.split())
    if _losing(a, b):
        return "LOSE"
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if _losing(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
