"""Wythoff game: decide win/lose and lexicographically minimal winning move."""


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    # losing positions are (floor(phi*n), floor(phi^2*n)) pairs (sorted)
    # brute force is fine for <=25 each
    N = 26
    lose = [[False] * N for _ in range(N)]
    # lose[i][j] = True means position (i,j) is losing for player to move
    for i in range(N):
        for j in range(N):
            if i == 0 and j == 0:
                lose[i][j] = True
                continue
            # a position (i,j) with i<=j; check moves
            ok = False
            # take from pile1 only
            for d in range(1, i + 1):
                if lose[i - d][j]:
                    ok = True
                    break
            if not ok:
                for d in range(1, j + 1):
                    if lose[i][j - d]:
                        ok = True
                        break
            if not ok:
                for d in range(1, min(i, j) + 1):
                    if lose[i - d][j - d]:
                        ok = True
                        break
            lose[i][j] = not ok
    if lose[a][b]:
        return "LOSE"
    # find lexicographically smallest (i,j) with i>=0,j>=0, not both 0,
    # resulting (a-i,b-j) losing
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            # move must be valid: take i from pile1 and j from pile2
            # allowed only if i==0 or j==0 (single pile) or i==j (both)
            if not (i == 0 or j == 0 or i == j):
                continue
            if lose[a - i][b - j]:
                best = (i, j)
                break
        if best is not None:
            break
    return "WIN " + str(best[0]) + " " + str(best[1])
