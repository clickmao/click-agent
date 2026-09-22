"""Wythoff game: take from one pile, or equal positive amounts from both."""


def _is_losing_exact(a: int, b: int) -> bool:
    x, y = (a, b) if a <= b else (b, a)
    d = y - x
    # Beatty sequence: lower Wythoff = floor(d*phi); verify exactly by integer search
    f = int(d * (1 + 5 ** 0.5) / 2.0)
    while (f + 1) * (f + 1 + d) <= x * (x + d):
        f += 1
    while f * (f + d) > x * (x + d):
        f -= 1
    return f == x


def solve(text: str) -> str:
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    a, b = (int(x) for x in lines[0].split()[:2])
    maxc = max(a, b)
    # losing[a][b] for all reachable positions (small bounds, exhaustive)
    losing = [[False] * (maxc + 1) for _ in range(maxc + 1)]
    for i in range(maxc + 1):
        for j in range(maxc + 1):
            if i == 0 and j == 0:
                losing[i][j] = True
                continue
            win = False
            for t in range(1, i + 1):
                if losing[i - t][j]:
                    win = True
                    break
            if not win:
                for t in range(1, j + 1):
                    if losing[i][j - t]:
                        win = True
                        break
            if not win:
                for t in range(1, min(i, j) + 1):
                    if losing[i - t][j - t]:
                        win = True
                        break
            losing[i][j] = not win
    if losing[a][b]:
        return 'LOSE'
    best = None
    # from first pile only: (i, 0)
    for i in range(1, a + 1):
        if losing[a - i][b]:
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    # from second pile only: (0, j)
    for j in range(1, b + 1):
        if losing[a][b - j]:
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    # equal amounts from both: (t, t)
    for t in range(1, min(a, b) + 1):
        if losing[a - t][b - t]:
            cand = (t, t)
            if best is None or cand < best:
                best = cand
    return 'WIN %d %d' % best
