def solve(text):
    first = text.split('\n')[0].split()
    a, b = int(first[0]), int(first[1])
    LIM = 30
    lose = [[False] * (LIM + 1) for _ in range(LIM + 1)]
    lose[0][0] = True
    for i in range(LIM + 1):
        for j in range(LIM + 1):
            if i == 0 and j == 0:
                continue
            ok = False
            for t in range(1, i + 1):
                if lose[i - t][j]:
                    ok = True
                    break
            if not ok:
                for t in range(1, j + 1):
                    if lose[i][j - t]:
                        ok = True
                        break
            if not ok:
                t = 1
                while t <= i and t <= j:
                    if lose[i - t][j - t]:
                        ok = True
                        break
                    t += 1
            lose[i][j] = not ok
    if lose[a][b]:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if lose[a - i][b - j]:
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN %d %d' % best
