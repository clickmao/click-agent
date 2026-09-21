"""Wythoff game: exact losing-set membership plus lexicographically smallest winning move."""


def _losing(a: int, b: int) -> bool:
    x, y = min(a, b), max(a, b)
    seen = [[False] * 26 for _ in range(26)]
    wins = [[False] * 26 for _ in range(26)]
    for i in range(26):
        for j in range(26):
            if i == 0 and j == 0:
                cur = False
            else:
                cur = False
                for ii in range(i + 1):
                    if seen[ii][j]:
                        cur = True
                        break
                if not cur:
                    for jj in range(j + 1):
                        if seen[i][jj]:
                            cur = True
                            break
                if not cur:
                    d = min(i, j)
                    for t in range(1, d + 1):
                        if seen[i - t][j - t]:
                            cur = True
                            break
                cur = not cur
            wins[i][j] = cur
            seen[i][j] = cur
    return not wins[x][y]


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if _losing(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i == 0 or j == 0 or i == j:
                if _losing(a - i, b - j):
                    if best is None or (i, j) < best:
                        best = (i, j)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
