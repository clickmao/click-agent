"""Wythoff's game: losing positions, otherwise lexicographically smallest move."""


_MOVES = []
for _i in range(0, 26):
    for _j in range(0, 26):
        _MOVES.append((_i, _j))


_WIN = [[False] * 26 for _ in range(26)]
for _a in range(25, -1, -1):
    for _b in range(25, -1, -1):
        if _a > 0 and not _WIN[_a - 1][_b]:
            _WIN[_a][_b] = True
        elif _b > 0 and not _WIN[_a][_b - 1]:
            _WIN[_a][_b] = True
        else:
            _d = 1
            while _a - _d >= 0 and _b - _d >= 0:
                if not _WIN[_a - _d][_b - _d]:
                    _WIN[_a][_b] = True
                    break
                _d += 1


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    a, b = (int(x) for x in lines[idx].split()[:2])

    if not _WIN[a][b]:
        return "LOSE"

    for i, j in _MOVES:
        if i > a or j > b:
            continue
        if i != 0 and j != 0 and i != j:
            continue
        if not _WIN[a - i][b - j]:
            return "WIN %d %d" % (i, j)
    return "LOSE"
