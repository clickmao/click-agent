def solve(text):
    a, b = map(int, text.split())

    def losing(x, y):
        if x < y:
            x, y = y, x
        d = x - y
        lo = int(d * 0.6180339887498949) - 2
        for k in range(max(0, lo), max(0, lo) + 5):
            if int(k * 1.6180339887498949) == y and k + d == x:
                return True
        return False

    if losing(a, b):
        return 'LOSE'

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j == 0) or (i == 0 and j > 0) or (i == j):
                if losing(a - i, b - j):
                    if best is None or (i, j) < best:
                        best = (i, j)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
