def solve(text: str) -> str:
    lines = text.split('\n')
    a, b = map(int, lines[0].split())
    losing = False
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i == j or i == 0 or j == 0:
                if a - i == 0 and b - j == 0:
                    pass
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i == j or i == 0 or j == 0:
                if a - i == 0 and b - j == 0:
                    losing = True
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i == j or i == 0 or j == 0:
                if a - i == 0 and b - j == 0:
                    return 'LOSE'
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == j or i == 0 or j == 0):
                continue
            na, nb = a - i, b - j
            if (na, nb) == (0, 0):
                return 'WIN ' + str(i) + ' ' + str(j)
            if _is_losing(na, nb):
                return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'


def _is_losing(a, b):
    if a > b:
        a, b = b, a
    for k in range(0, 30):
        x = (k * (1 + 5 ** 0.5)) / 2.0
        ax = int(x)
        bx = ax + k
        if ax == a and bx == b:
            return True
        if ax > a or bx > b:
            return False
    return False
