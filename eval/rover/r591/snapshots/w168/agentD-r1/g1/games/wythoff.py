"""Wythoff's game: losing positions and lexicographically smallest winning move."""


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])

    # win[x][y] = True iff the player to move with (x, y) stones wins.
    win = [[False] * (b + 1) for _ in range(a + 1)]
    for x in range(a + 1):
        for y in range(b + 1):
            if x == 0 and y == 0:
                continue
            w = False
            for t in range(1, x + 1):
                if not win[x - t][y]:
                    w = True
                    break
            if not w:
                for t in range(1, y + 1):
                    if not win[x][y - t]:
                        w = True
                        break
            if not w:
                d = min(x, y)
                for t in range(1, d + 1):
                    if not win[x - t][y - t]:
                        w = True
                        break
            win[x][y] = w

    if not win[a][b]:
        return "LOSE"

    best = None
    # Single-pile removals.
    for i in range(1, a + 1):
        if not win[a - i][b]:
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
            break
    for j in range(1, b + 1):
        if not win[a][b - j]:
            cand = (0, j)
            if best is None or cand < best:
                best = cand
            break
    # Equal removals from both piles.
    for t in range(1, min(a, b) + 1):
        if not win[a - t][b - t]:
            cand = (t, t)
            if best is None or cand < best:
                best = cand
            break

    i, j = best
    return "WIN %d %d" % (i, j)
