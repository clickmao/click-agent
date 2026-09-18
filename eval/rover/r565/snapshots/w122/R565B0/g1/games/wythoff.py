def is_lose(a: int, b: int) -> bool:
    a, b = min(a, b), max(a, b)
    d = b - a
    return a == int(d * ((1 + 5 ** 0.5) / 2))


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if is_lose(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
