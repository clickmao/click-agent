def _is_lose(a, b):
    if a > b:
        a, b = b, a
    if a == 0:
        return b == 0
    d = b - a
    return a == int(d * (1 + 5 ** 0.5) / 2)


def _moves(a, b):
    for i in range(a + 1):
        yield i, 0
    for j in range(1, b + 1):
        yield 0, j
    for c in range(1, min(a, b) + 1):
        yield c, c


def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    if _is_lose(a, b):
        return "LOSE"
    candidates = []
    for i, j in _moves(a, b):
        if i == 0 and j == 0:
            continue
        if _is_lose(a - i, b - j):
            candidates.append((i, j))
    candidates.sort()
    i, j = candidates[0]
    return "WIN " + str(i) + " " + str(j)
