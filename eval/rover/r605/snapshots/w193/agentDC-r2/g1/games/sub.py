"""Subtraction game: decide win/lose and the smallest winning first move."""


def solve(text: str) -> str:
    lines = text.splitlines()
    if not lines:
        return "LOSE"
    n, k = map(int, lines[0].split())
    moves = sorted(map(int, lines[1].split())) if len(lines) > 1 else []

    # win[x] = True if the player to move with x stones can force a win
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in moves:
            if s > x:
                break
            if not win[x - s]:
                win[x] = True
                break

    if not win[n]:
        return "LOSE"
    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN " + str(s)
    return "LOSE"
