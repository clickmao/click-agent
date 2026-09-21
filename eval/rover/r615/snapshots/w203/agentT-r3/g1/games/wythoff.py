"""Wythoff 博弈：字典序最小的必胜着法。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    a, b = map(int, lines[0].split())
    win = [[False] * (b + 1) for _ in range(a + 1)]
    for x in range(a + 1):
        for y in range(b + 1):
            if x == 0 and y == 0:
                continue
            ok = False
            for i in range(1, x + 1):
                if not win[x - i][y]:
                    ok = True
                    break
            if not ok:
                for j in range(1, y + 1):
                    if not win[x][y - j]:
                        ok = True
                        break
            if not ok:
                for t in range(1, min(x, y) + 1):
                    if not win[x - t][y - t]:
                        ok = True
                        break
            win[x][y] = ok
    if not win[a][b]:
        return 'LOSE'
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if not win[a - i][b - j]:
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
