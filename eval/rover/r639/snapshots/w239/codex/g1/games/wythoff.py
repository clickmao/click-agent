def solve(text: str) -> str:
    a, b = map(int, text.split())

    limit = 30
    losing = []
    for i in range(0, limit):
        row = [False] * limit
        for j in range(0, limit):
            ok = True
            for (x, y) in losing:
                if x == i or y == j or (i - x) == (j - y):
                    ok = False
                    break
            if ok:
                losing.append((i, j))
            row[j] = ok
    losing_set = set(losing)

    if (a, b) in losing_set:
        return 'LOSE'

    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (a - i, b - j) in losing_set:
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
