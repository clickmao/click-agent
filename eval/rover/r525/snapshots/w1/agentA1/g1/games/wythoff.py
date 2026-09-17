"""Wythoff's game: decide LOSE, else lexicographically smallest winning move."""


def _is_losing(a: int, b: int, memo={}) -> bool:
    """Cold positions are those with no move into a cold position."""
    key = (a, b)
    if key in memo:
        return memo[key]
    return False  # placeholder, recomputed below


def solve(text: str) -> str:
    tokens = []
    for line in text.split("\n"):
        tokens.extend(line.split())
    it = iter(tokens)
    a = int(next(it))
    b = int(next(it))

    MA = 30  # positions can move downward; a,b <= 25 so 0..25 suffices, keep margin

    # lose[x][y]: True if position (x, y) is a cold (losing for player to move)
    lose = [[False] * (MA + 1) for _ in range(MA + 1)]
    for x in range(MA + 1):
        for y in range(MA + 1):
            if x == 0 and y == 0:
                lose[x][y] = True
                continue
            # enumerate all moves to see if any leads to a losing position
            has_win = False
            # take from pile 1 only
            for i in range(1, x + 1):
                if lose[x - i][y]:
                    has_win = True
                    break
            if not has_win:
                for j in range(1, y + 1):
                    if lose[x][y - j]:
                        has_win = True
                        break
            if not has_win:
                for t in range(1, min(x, y) + 1):
                    if lose[x - t][y - t]:
                        has_win = True
                        break
            lose[x][y] = not has_win

    if lose[a][b]:
        return "LOSE"

    # find lexicographically smallest (i, j): i ascending, then j ascending
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            # a move removing i from first, j from second; valid iff
            # i == 0 (only second), j == 0 (only first), or i == j (both)
            if not (i == 0 or j == 0 or i == j):
                continue
            if i <= a and j <= b and lose[a - i][b - j]:
                return "WIN %d %d" % (i, j)
    return "LOSE"
