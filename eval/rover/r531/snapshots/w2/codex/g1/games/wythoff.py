LIMIT = 25

_LOSE = [[False] * (LIMIT + 1) for _ in range(LIMIT + 1)]
for _s in range(0, 2 * LIMIT + 1):
    for _x in range(0, LIMIT + 1):
        _y = _s - _x
        if _y < 0 or _y > LIMIT:
            continue
        if _x == 0 and _y == 0:
            _LOSE[_x][_y] = True
            continue
        _ok = True
        for _i in range(1, _x + 1):
            if _LOSE[_x - _i][_y]:
                _ok = False
                break
        if _ok:
            for _j in range(1, _y + 1):
                if _LOSE[_x][_y - _j]:
                    _ok = False
                    break
        if _ok:
            for _t in range(1, min(_x, _y) + 1):
                if _LOSE[_x - _t][_y - _t]:
                    _ok = False
                    break
        _LOSE[_x][_y] = _ok


def _is_lose(x, y):
    return _LOSE[x][y]


def solve(text: str) -> str:
    a, b = map(int, text.split())
    if _is_lose(a, b):
        return 'LOSE'
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if _is_lose(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
