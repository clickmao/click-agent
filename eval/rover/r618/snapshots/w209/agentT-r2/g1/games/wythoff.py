_PHI = (1 + 5 ** 0.5) / 2
_LOSE = set()
for _n in range(0, 30):
    _a = int(_n * _PHI)
    _b = _a + _n
    for _t in range(_n - 2, _n + 3):
        if _t < 0:
            continue
        _ta = int(_t * _PHI)
        _tb = _ta + _t
        _LOSE.add((_ta, _tb))
for _t in range(0, 30):
    _ta = int(_t * _PHI)
    _LOSE.add((_ta, _ta + _t))


def _lose(a, b):
    if a > b:
        a, b = b, a
    return (a, b) in _LOSE


def solve(text: str) -> str:
    a, b = map(int, text.split())
    if _lose(a, b):
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i == j or i == 0 or j == 0:
                if _lose(a - i, b - j):
                    cand = (i, j)
                    if best is None or cand < best:
                        best = cand
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
