"""Subtraction game: two players alternately remove an allowed number of stones.

stdin:  first line "n k" (n stones, k allowed move sizes);
        second line k distinct integers s1..sk (contains 1).
stdout: "WIN m" (m = numerically smallest winning first move) if the first
        player has a winning strategy, else "LOSE".

Normal play: whoever takes the last stone wins.
"""


def solve(text: str) -> str:
    """Pure function: full stdin text -> full stdout text (no trailing newline)."""
    lines = text.splitlines()
    if not lines:
        return ""
    n, k = (int(x) for x in lines[0].split())
    moves = [int(x) for x in lines[1].split()][:k]
    moves.sort()

    # win[i] == True  <=>  position with i stones is a win for the player to move
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    for s in moves:  # ascending -> numerically smallest winning move
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"  # unreachable for consistent input
