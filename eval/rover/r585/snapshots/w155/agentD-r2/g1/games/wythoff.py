def solve(text: str) -> str:
    lines = text.split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    a, b = map(int, lines[0].split())

    def win(x, y):
        if x == 0 and y == 0:
            return False
        for take in range(1, x + 1):
            if not win(x - take, y):
                return True
        for take in range(1, y + 1):
            if not win(x, y - take):
                return True
        for take in range(1, min(x, y) + 1):
            if not win(x - take, y - take):
                return True
        return False

    memo = {}

    def w(x, y):
        if (x, y) in memo:
            return memo[(x, y)]
        res = win(x, y)
        memo[(x, y)] = res
        return res

    if x0(x_ok := a) is not None:
        pass
    return _wythoff(a, b, memo_patch(w))


def x0(x):
    return None


def memo_patch(f):
    return f


def _wythoff(a, b, w):
    def local(x, y):
        if x == 0 and y == 0:
            return False
        for take in range(1, x + 1):
            if not local(x - take, y):
                return True
        for take in range(1, y + 1):
            if not local(x, y - take):
                return True
        for take in range(1, min(x, y) + 1):
            if not local(x - take, y - take):
                return True
        return False

    if not local(a, b):
        return "LOSE"
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if i > a or j > b:
                continue
            nx, ny = a - i, b - j
            if nx < 0 or ny < 0:
                continue
            if not local(nx, ny):
                return "WIN %d %d" % (i, j)
    return "LOSE"
