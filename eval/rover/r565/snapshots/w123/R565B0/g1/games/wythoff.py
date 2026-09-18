LIM = 40


def _build():
    lose = [[False] * (LIM + 1) for _ in range(LIM + 1)]
    # win[i][j] = True 表示 (i, j) 是先手必胜
    win = [[False] * (LIM + 1) for _ in range(LIM + 1)]
    for s in range(0, 2 * LIM + 1):
        for i in range(0, LIM + 1):
            j = s - i
            if j < 0 or j > LIM:
                continue
            if i == 0 and j == 0:
                win[0][0] = False
                continue
            res = False
            for k in range(1, i + 1):
                if not win[i - k][j]:
                    res = True
                    break
            if not res:
                for k in range(1, j + 1):
                    if not win[i][j - k]:
                        res = True
                        break
            if not res:
                for k in range(1, min(i, j) + 1):
                    if not win[i - k][j - k]:
                        res = True
                        break
            win[i][j] = res
    return win


_WIN = None


def solve(text: str) -> str:
    global _WIN
    if _WIN is None:
        _WIN = _build()
    lines = text.splitlines()
    a, b = map(int, lines[0].split())

    if a >= len(_WIN) or b >= len(_WIN[a]):
        LIM2 = max(a, b) + 1
        _WIN = _build2(LIM2)

    if not _WIN[a][b]:
        return "LOSE"

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            ni, nj = a - i, b - j
            if not _WIN[ni][nj]:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best


def _build2(limit):
    win = [[False] * (limit + 1) for _ in range(limit + 1)]
    for s in range(0, 2 * limit + 1):
        for i in range(0, limit + 1):
            j = s - i
            if j < 0 or j > limit:
                continue
            if i == 0 and j == 0:
                win[0][0] = False
                continue
            res = False
            for k in range(1, i + 1):
                if not win[i - k][j]:
                    res = True
                    break
            if not res:
                for k in range(1, j + 1):
                    if not win[i][j - k]:
                        res = True
                        break
            if not res:
                for k in range(1, min(i, j) + 1):
                    if not win[i - k][j - k]:
                        res = True
                        break
            win[i][j] = res
    return win
