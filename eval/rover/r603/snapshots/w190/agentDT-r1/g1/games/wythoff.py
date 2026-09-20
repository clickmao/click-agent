def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])

    # P-positions (losing positions) of Wythoff's game are (floor(n*phi), floor(n*phi^2)).
    def is_losing(x, y):
        if x > y:
            x, y = y, x
        # find candidate n roughly: n ~ x / phi
        import math
        phi = (1.0 + math.sqrt(5.0)) / 2.0
        n0 = int(x / phi)
        for n in range(max(0, n0 - 3), n0 + 4):
            px = int(math.floor(n * phi))
            py = px + n
            if px == x and py == y:
                return True
        return False

    if is_losing(a, b):
        return 'LOSE'

    best_i = None
    best_j = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            na = a - i
            nb = b - j
            if is_losing(na, nb):
                if best_i is None or (i, j) < (best_i, best_j):
                    best_i, best_j = i, j
    return 'WIN ' + str(best_i) + ' ' + str(best_j)
