LIM = 25

MOVE_TAKE_ONE = 0
MOVE_TAKE_BOTH = 1


def _build_losing(lim):
    losing = [[False] * (lim + 1) for _ in range(lim + 1)]
    for a in range(0, lim + 1):
        for b in range(0, lim + 1):
            if a == 0 and b == 0:
                losing[a][b] = True
                continue
            ok = True
            for kind in (MOVE_TAKE_ONE, MOVE_TAKE_BOTH):
                if kind == MOVE_TAKE_ONE:
                    for da in range(0, a):
                        if losing[da][b]:
                            ok = False
                            break
                    if ok:
                        for db in range(0, b):
                            if losing[a][db]:
                                ok = False
                                break
                else:
                    t = min(a, b)
                    for d in range(1, t + 1):
                        if losing[a - d][b - d]:
                            ok = False
                            break
                if not ok:
                    break
            losing[a][b] = ok
    return losing


_LOSING = _build_losing(LIM)


def _is_move(a, b, i, j):
    if i == 0 and j == 0:
        return False
    if i < 0 or j < 0 or i > a or j > b:
        return False
    if i == 0 or j == 0:
        return True
    if i == j:
        return True
    return False


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    if _LOSING[a][b]:
        return 'LOSE'
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i == a and j == b:
                continue
            if _is_move(a, b, i, j) and _LOSING[i][j]:
                return 'WIN %d %d' % (a - i, b - j)
    return 'LOSE'
