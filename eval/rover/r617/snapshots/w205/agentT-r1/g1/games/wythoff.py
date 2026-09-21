_P = []
_Q = []

def _loses(x, y):
    if not _P:
        a0, b0 = 0, 0
        i = 1
        while True:
            a = a0 + i
            b = a + i
            _P.append(a)
            _Q.append(b)
            a0 = a
            i += 1
            if a >= 25:
                return
    for i in range(len(_P)):
        if _P[i] == x and _Q[i] == y:
            return True
        if _Q[i] == x and _P[i] == y:
            return True
    return False

def _loses_order_is_py(x, y):
    return _loses(x, y)

def solve(text: str) -> str:
    a, b = map(int, text.split())
    _loses(0, 0)
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            valid = False
            if j == 0:
                valid = True
            elif i == 0:
                valid = True
            elif i == j:
                valid = True
            if not valid:
                continue
            if _loses(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
