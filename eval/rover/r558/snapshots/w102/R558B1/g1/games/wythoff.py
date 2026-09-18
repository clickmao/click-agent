"""Wythoff 博弈：必败点判定与字典序最小必胜着法。"""


LIMIT = 25


def _lose_table():
    # lose[a][b] 为 True 表示两堆分别为 a、b 时先手必败（对称）
    lose = [[False] * (LIMIT + 1) for _ in range(LIMIT + 1)]
    for a in range(LIMIT + 1):
        for b in range(LIMIT + 1):
            if a == 0 and b == 0:
                lose[a][b] = True
                continue
            ok = False
            # 从第一堆取 i
            for i in range(1, a + 1):
                if lose[a - i][b]:
                    ok = True
                    break
            if not ok:
                # 从第二堆取 j
                for j in range(1, b + 1):
                    if lose[a][b - j]:
                        ok = True
                        break
            if not ok:
                # 同时取相同 t
                for t in range(1, min(a, b) + 1):
                    if lose[a - t][b - t]:
                        ok = True
                        break
            lose[a][b] = not ok
    return lose


_LOSE = _lose_table()


def solve(text: str) -> str:
    data = text.split()
    a = int(data[0])
    b = int(data[1])
    if _LOSE[a][b]:
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _LOSE[a - i][b - j]:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return "WIN %d %d" % best
