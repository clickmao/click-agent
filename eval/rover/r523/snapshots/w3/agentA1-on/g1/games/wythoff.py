"""Wythoff 博弈: 必败点判定 + 字典序最小的必胜着法.

stdin: 一行两个整数 a b.
stdout: `LOSE` 或 `WIN i j` (i=从第一堆取, j=从第二堆取, i,j>=0 不同时为 0).
"""


def _lose_table(limit):
    """返回 (limit+1)x(limit+1) 必败点布尔表.

    状态 (a,b) 必败 <=> 所有合法走法都到达必胜态.
    合法走法: 单堆取任意正数, 或两堆同取相同正数.
    """
    lose = [[False] * (limit + 1) for _ in range(limit + 1)]
    lose[0][0] = True
    for a in range(limit + 1):
        for b in range(limit + 1):
            if a == 0 and b == 0:
                continue
            win = False
            for i in range(1, a + 1):
                if lose[a - i][b]:
                    win = True
                    break
            if not win:
                for j in range(1, b + 1):
                    if lose[a][b - j]:
                        win = True
                        break
            if not win:
                for d in range(1, min(a, b) + 1):
                    if lose[a - d][b - d]:
                        win = True
                        break
            lose[a][b] = not win
    return lose


def solve(text):
    a, b = [int(x) for x in text.split()[:2]]
    limit = max(a, b)
    lose = _lose_table(limit)
    if lose[a][b]:
        return "LOSE"
    # 枚举全部合法走法, 取使对手落入必败态者中 (i,j) 字典序最小
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            same = (i == j)                    # 两堆同取
            single = (i == 0 or j == 0)        # 单堆取
            if not (same or single):
                continue
            if lose[a - i][b - j]:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    i, j = best
    return "WIN %d %d" % (i, j)
