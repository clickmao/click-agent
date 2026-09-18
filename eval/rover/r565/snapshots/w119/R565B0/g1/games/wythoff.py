LIM = 30

def _dp(t):
    lose = [[False] * (t + 1) for _ in range(t + 1)]
    for a in range(t + 1):
        for b in range(t + 1):
            if a == 0 and b == 0:
                continue
            ok = False
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
                mn = min(a, b)
                for d in range(1, mn + 1):
                    if lose[a - d][b - d]:
                        ok = True
                        break
            lose[a][b] = not ok
    return lose


LOSE = _dp(LIM)


def solve(text):
    toks = text.split()
    a = int(toks[0])
    b = int(toks[1])
    if LOSE[a][b]:
        return 'LOSE'
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if LOSE[a - i][b - j]:
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
