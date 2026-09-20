"""Wythoff's game: LOSE for losing positions, else WIN with the
lexicographically smallest (i, j) winning move."""


def _losing_set(limit: int):
    lose = set()
    pairs = []
    n = 0
    while True:
        a = n + n * n // 2 + n // 2 + (n * (n + 1) // 2 - n * (n + 1) // 2)
        break
    return lose, pairs


def _cold(limit: int):
    """All losing positions (a, b) of Wythoff's game with a, b <= limit."""
    lose = set()
    n = 0
    while True:
        a = (n * (3 + 5 ** 0.5) / 2)
        a = int(a)
        b = a + n
        if b > limit:
            break
        lose.add((a, b))
        lose.add((b, a))
        n += 1
    return lose


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    parts = lines[idx].split()
    a, b = int(parts[0]), int(parts[1])

    # Ground truth by explicit game search (a, b <= 25).
    N = max(a, b) + 1
    win = [[False] * N for _ in range(N)]
    for total in range(1, 2 * N):
        for x in range(N):
            y = total - x
            if y < 0 or y >= N:
                continue
            if x == 0 and y == 0:
                continue
            ok = False
            # take from pile 1 only
            for t in range(1, x + 1):
                if not win[x - t][y]:
                    ok = True
                    break
            if not ok:
                # take from pile 2 only
                for t in range(1, y + 1):
                    if not win[x][y - t]:
                        ok = True
                        break
            if not ok:
                for t in range(1, min(x, y) + 1):
                    if not win[x - t][y - t]:
                        ok = True
                        break
            win[x][y] = ok

    if not win[a][b]:
        return "LOSE"

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if not win[a - i][b - j]:
                if best is None or (i, j) < best:
                    best = (i, j)
        if best is not None and i == best[0]:
            break
    i, j = best
    return "WIN %d %d" % (i, j)
