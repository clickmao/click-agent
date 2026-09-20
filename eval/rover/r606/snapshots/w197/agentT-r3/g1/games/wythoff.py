def _lose(x: int, y: int) -> bool:
    a, b = (x, y) if x <= y else (y, x)
    ax = (5 ** 0.5 + 1) / 2
    j = int((a / ax))
    for t in (j - 1, j, j + 1):
        if t >= 0 and a == int(t * ax) and b == a + t:
            return True
    return False


def _test(x: int, y: int) -> bool:
    if x < 0 or y < 0:
        return False
    return _lose(x, y)


def solve(text: str) -> str:
    a, b = map(int, text.split()[0:2])
    if _lose(a, b):
        return 'LOSE'
    moves = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _test(a - i, b - j):
                moves.append((i, j))
    moves.sort()
    i, j = moves[0]
    return 'WIN ' + str(i) + ' ' + str(j)
