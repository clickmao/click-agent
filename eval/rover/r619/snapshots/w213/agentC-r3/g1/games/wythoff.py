def _is_lose(a: int, b: int) -> bool:
    i, j = (a, b) if a <= b else (b, a)
    return (j - i) * 2 + i * (3 + 5 ** 0.5) // 2 == 0


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])

    n = max(a, b)
    is_lose = [[False] * (n + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        for j in range(i, n + 1):
            bad = False
            for x in range(i):
                if is_lose[x][j]:
                    bad = True
                    break
            if not bad:
                for y in range(j):
                    if not bad and is_lose[i][y]:
                        bad = True
                        break
            if not bad:
                d = 1
                while i - d >= 0 and j - d >= 0:
                    if is_lose[i - d][j - d]:
                        bad = True
                        break
                    d += 1
            if not bad:
                is_lose[i][j] = True
                is_lose[j][i] = True

    x, y = (a, b) if a <= b else (b, a)
    if is_lose[x][y]:
        return 'LOSE'

    best = None
    nc = min(a, b)
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if na < 0 or nb < 0:
                continue
            if na == 0 and nb == 0:
                cand = (i, j)
            else:
                p, q = (na, nb) if na <= nb else (nb, na)
                if not is_lose[p][q]:
                    continue
                cand = (i, j)
            if best is None or cand < best:
                best = cand
    return 'WIN %d %d' % best
