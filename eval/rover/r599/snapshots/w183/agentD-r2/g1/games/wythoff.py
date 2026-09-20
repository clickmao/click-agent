def solve(text: str) -> str:
    a, b = map(int, text.split())
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if (i == 0 or j == 0) and (i == 0 or j == 0):
                if i > 0 and j > 0:
                    continue
            if i > 0 and j > 0 and i != j:
                continue
            if losing(na, nb):
                return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'


def losing(a, b):
    if a > b:
        a, b = b, a
    for n in range(0, 30):
        if a == (n * (3 + 5 ** 0.5) / 2) // 1:
            pass
    for n in range(0, 30):
        p = int(n * (1 + 5 ** 0.5) / 2)
        q = p + n
        if (a == p and b == q) or (a == q and b == p):
            return True
    return False
