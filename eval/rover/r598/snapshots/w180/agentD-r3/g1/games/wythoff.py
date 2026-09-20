def solve(text: str) -> str:
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    a, b = map(int, lines[0].split())
    n = 32
    win = [[False] * (n + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        for j in range(n + 1):
            if i == 0 and j == 0:
                win[i][j] = False
                continue
            res = False
            for x in range(1, i + 1):
                if not win[i - x][j]:
                    res = True
                    break
            if not res:
                for y in range(1, j + 1):
                    if not win[i][j - y]:
                        res = True
                        break
            if not res:
                for t in range(1, min(i, j) + 1):
                    if not win[i - t][j - t]:
                        res = True
                        break
            win[i][j] = res
    if not win[a][b]:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        rem_a = a - i
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            same = (i == j)
            one_pile = (i == 0) or (j == 0)
            if not same and not one_pile:
                continue
            if not win[rem_a][b - j]:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return 'WIN %d %d' % best
