"""Subtraction game: win/lose and the smallest winning first move."""


def solve(text: str) -> str:
    lines = text.split("\n")
    if lines and lines[0] == "":
        lines = lines[1:]
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
    for s in moves:  # moves ascending -> smallest winning move
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
