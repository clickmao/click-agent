def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    moves = []
    for i in range(1, a + 1):
        if not losing(a - i, b):
            moves.append((i, 0))
    for j in range(1, b + 1):
        if not losing(a, b - j):
            moves.append((0, j))
    for c in range(1, min(a, b) + 1):
        if not losing(a - c, b - c):
            moves.append((c, c))
    if not moves:
        return 'LOSE'
    moves.sort()
    i, j = moves[0]
    return 'WIN ' + str(i) + ' ' + str(j)


def losing(x, y):
    # Wythoff P-positions: (floor(m*phi), floor(m*phi*phi))
    if x > y:
        x, y = y, x
    m = y - x
    if m < 0:
        return False
    phi = (1 + 5 ** 0.5) / 2
    a = int(m * phi)
    return x == a and y == a + m
