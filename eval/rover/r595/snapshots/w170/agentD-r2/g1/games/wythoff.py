LIM = 30


def _losing(a, b):
    for x in range(a + 1):
        for y in range(b + 1):
            if x == 0 and y == 0:
                continue
            if x == y and x > 0:
                if a - x == 0 and b - y == 0:
                    return True
            if y == 0 and x > 0:
                if a - x == 0 and b == 0:
                    return True
            if x == 0 and y > 0:
                if a == 0 and b - y == 0:
                    return True
    return False


def solve(text):
    lines = text.splitlines()
    a, b = map(int, lines[0].split())
    memo = {}

    def losing(x, y):
        if x > y:
            x, y = y, x
        key = (x, y)
        if key in memo:
            return memo[key]
        res = False
        for i in range(x + 1):
            if losing(x - i, y):
                res = True
                break
        if not res:
            for j in range(y + 1):
                if j == 0:
                    continue
                if losing(x, y - j):
                    res = True
                    break
        if not res:
            t = min(x, y)
            for d in range(1, t + 1):
                if losing(x - d, y - d):
                    res = True
                    break
        memo[key] = res
        return res

    memo[(0, 0)] = False
    if losing(a, b):
        return 'WIN 0 0'
    cur = losing(a, b)
    if not cur:
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            ok = False
            if i > 0 and j == 0:
                ok = losing(a - i, b)
            elif i == 0 and j > 0:
                ok = losing(a, b - j)
            elif i == j:
                ok = losing(a - i, b - j)
            if ok:
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
