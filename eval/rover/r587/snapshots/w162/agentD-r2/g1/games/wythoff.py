_LIMIT = 40
_LO = [[False] * (_LIMIT + 1) for _ in range(_LIMIT + 1)]
for _i in range(_LIMIT + 1):
    for _j in range(_i, _LIMIT + 1):
        ok = False
        for _a in range(_i):
            if _LO[_a][_j]:
                ok = True
                break
        if not ok:
            for _b in range(_j):
                if _LO[_i][_b]:
                    ok = True
                    break
        if not ok:
            _d = min(_i, _j)
            for _t in range(1, _d + 1):
                if _LO[_i - _t][_j - _t]:
                    ok = True
                    break
        _LO[_i][_j] = not ok
        _LO[_j][_i] = _LO[_i][_j]


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if _LO[a][b]:
        return "LOSE"
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            valid = False
            if i == 0 or j == 0:
                valid = True
            elif i == j:
                valid = True
            if valid and _LO[a - i][b - j]:
                if best is None or (i, j) < best:
                    best = (i, j)
    return "WIN %d %d" % best
