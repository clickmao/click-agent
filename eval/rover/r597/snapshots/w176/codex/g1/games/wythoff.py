from math import isqrt

AX = 40


def _lose_table(limit: int):
    lose = [[False] * (limit + 1) for _ in range(limit + 1)]
    for a in range(limit + 1):
        for b in range(limit + 1):
            if a == 0 and b == 0:
                lose[a][b] = True
                continue
            ok = False
            # remove from pile 1 only
            for i in range(1, a + 1):
                if lose[a - i][b]:
                    ok = True
                    break
            if not ok:
                for j in range(1, b + 1):
                    if lose[a][b - j]:
                        ok = True
                        break
            if not ok:
                for t in range(1, min(a, b) + 1):
                    if lose[a - t][b - t]:
                        ok = True
                        break
            lose[a][b] = not ok
    return lose


_TABLE = _lose_table(AX)


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    if _TABLE[a][b]:
        return "LOSE"

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if _TABLE[a - i][b - j]:
                best = (i, j)
                break
        if best is not None:
            break
    return "WIN %d %d" % best
