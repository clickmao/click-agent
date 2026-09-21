def solve(text):
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    moves = []
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            moves.append((i, j))
    moves.sort()
    for i, j in moves:
        na, nb = a - i, b - j
        if is_losing(na, nb):
            return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'


def is_losing(a, b):
    if a == 0 and b == 0:
        return True
    if a == 0 or b == 0:
        return False
    x, y = (a, b) if a <= b else (b, a)
    for t in range(1, x + 1):
        if int(t * (1 + 5 ** 0.5) / 2) == x and t + int(t * (1 + 5 ** 0.5) / 2) == y:
            return True
    return False
