LIMIT = 40

BAD = set()
_mex = [False] * (LIMIT + 1)
_used_second = [False] * (2 * LIMIT + 2)
for _k in range(LIMIT + 1):
    _a = 0
    while _mex[_a]:
        _a += 1
    _b = _a + _k
    if _b > 2 * LIMIT + 1:
        break
    _mex[_a] = True
    _used_second[_b] = True
    BAD.add((_a, _b))
    BAD.add((_b, _a))


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    a, b = map(int, lines[idx].split()[:2])
    if (a, b) in BAD:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        j_opt = b - (a - i) if 0 <= b - (a - i) <= b else None
        for j in (0, j_opt):
            if j is None or j < 0 or j > b or (i == 0 and j == 0):
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if (a - i, b - j) in BAD:
                if best is None or (i, j) < best:
                    best = (i, j)
        if i == 0:
            for j in range(b + 1):
                if j == 0:
                    continue
                if (a, b - j) in BAD:
                    if best is None or (0, j) < best:
                        best = (0, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
