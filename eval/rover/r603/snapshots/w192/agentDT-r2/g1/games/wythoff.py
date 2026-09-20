def solve(text):
    data = text.split()
    a = int(data[0])
    b = int(data[1])

    def losing(x, y):
        if x > y:
            x, y = y, x
        i = 0
        while True:
            p = i * (1 + 5 ** 0.5) / 2
            pi = int(p)
            if pi > x:
                break
            if pi == x and pi + i == y:
                return True
            i += 1
        return False

    if losing(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if i > 0 and j > 0 and i != j:
                continue
            if losing(na, nb):
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN %d %d' % best
