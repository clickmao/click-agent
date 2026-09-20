"""Wythoff's game: lexicographically smallest winning move, or LOSE."""


def solve(text: str) -> str:
    tokens = text.split()
    a, b = int(tokens[0]), int(tokens[1])

    # lose[x][y] == True iff (x, y) is a losing position for the player to move.
    limit = max(a, b)
    lose = [[False] * (limit + 1) for _ in range(limit + 1)]
    for x in range(limit + 1):
        for y in range(limit + 1):
            if x == 0 and y == 0:
                lose[x][y] = True
                continue
            can_win = False
            # take from one pile only
            for i in range(1, x + 1):
                if lose[x - i][y]:
                    can_win = True
                    break
            if not can_win:
                for j in range(1, y + 1):
                    if lose[x][y - j]:
                        can_win = True
                        break
            if not can_win:
                # take the same positive amount from both piles
                for t in range(1, min(x, y) + 1):
                    if lose[x - t][y - t]:
                        can_win = True
                        break
            lose[x][y] = not can_win

    if lose[a][b]:
        return "LOSE"

    # lexicographically smallest (i, j), i then j
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            # move must be legal: only one pile, or equal amounts from both
            if i > 0 and j > 0 and i != j:
                continue
            if lose[a - i][b - j]:
                return "WIN %d %d" % (i, j)
    return "LOSE"
