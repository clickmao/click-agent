def solve(text: str) -> str:
    a, b = map(int, text.split()[0:2])

    def is_losing(x, y):
        for i in range(x + 1):
            for j in range(y + 1):
                if i == 0 and j == 0:
                    continue
                if i > 0 and j > 0 and i != j:
                    continue
                nx, ny = x - i, y - j
                if not is_losing(nx, ny):
                    return False
        return True

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if is_losing(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
