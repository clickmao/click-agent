"""Game `sub`: subtraction game, first-player win/lose decision.

Input : first line "n k" (1<=n<=80 stones, 1<=k<=12 number of allowed moves);
        second line k distinct integers s1..sk (1<=si<=12, 1 is guaranteed present).
Output: "WIN m" with the numerically smallest winning first move m when the
        first player has a winning strategy, otherwise "LOSE".

Play: players alternately remove exactly one allowed amount; the player taking
the last stone wins (normal play).
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    n, k = (int(x) for x in lines[0].split())
    moves = sorted(int(x) for x in lines[1].split())[:k]

    # win[i] = True iff the player to move with i stones can force a win.
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
