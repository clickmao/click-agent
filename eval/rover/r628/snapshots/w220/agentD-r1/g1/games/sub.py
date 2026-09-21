"""Subtraction game: win/lose and smallest winning first move."""


def solve(text: str) -> str:
    lines = text.split()
    n = int(lines[0])
    k = int(lines[1])
    moves = sorted(int(x) for x in lines[2:2 + k])
    # win[i] = True if the player to move with i stones can force a win
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        w = False
        for s in moves:
            if s > i:
                continue
            if not win[i - s]:
                w = True
                break
        win[i] = w
    if not win[n]:
        return "LOSE"
    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN {}".format(s)
    return "LOSE"
