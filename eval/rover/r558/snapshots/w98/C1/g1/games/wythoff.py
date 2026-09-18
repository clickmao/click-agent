def _losing(maxn: int):
    lose = [[False] * (maxn + 1) for _ in range(maxn + 1)]
    for a in range(maxn + 1):
        for b in range(maxn + 1):
            if a == 0 and b == 0:
                lose[a][b] = True
                continue
            ok = True
            for i in range(1, a + 1):
                if lose[a - i][b]:
                    ok = False
                    break
            if ok:
                for j in range(1, b + 1):
                    if lose[a][b - j]:
                        ok = False
                        break
            if ok:
                for t in range(1, min(a, b) + 1):
                    if lose[a - t][b - t]:
                        ok = False
                        break
            lose[a][b] = ok
    return lose


_LOSE = _losing(25)


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while lines[idx].strip() == '':
        idx += 1
    a, b = (int(x) for x in lines[idx].split())
    if _LOSE[a][b]:
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _LOSE[a - i][b - j]:
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
