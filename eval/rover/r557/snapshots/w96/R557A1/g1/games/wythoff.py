"""Wythoff 博弈：WIN i j（字典序最小）/ LOSE。"""


def solve(text: str) -> str:
    toks = text.split()
    if not toks:
        return ""
    a, b = int(toks[0]), int(toks[1])
    win = [[False] * (b + 1) for _ in range(a + 1)]
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            res = False
            for ii in range(i):
                if not win[ii][j]:
                    res = True
                    break
            if not res:
                for jj in range(j):
                    if not win[i][jj]:
                        res = True
                        break
            if not res:
                t = min(i, j)
                for d in range(1, t + 1):
                    if not win[i - d][j - d]:
                        res = True
                        break
            win[i][j] = res
    if not win[a][b]:
        return "LOSE"
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not win[a - i][b - j]:
                return "WIN %d %d" % (i, j)
    return "LOSE"
