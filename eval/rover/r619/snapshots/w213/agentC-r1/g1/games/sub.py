"""Subtraction game: decide win/lose and minimal winning first move."""


def solve(text: str) -> str:
    lines = text.split("\n")
    n, k = map(int, lines[0].split())
    moves = sorted(map(int, lines[1].split()))
    _ = k
    # win[i] = True if player to move with i stones (i>=0) wins
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        w = False
        for s in moves:
            if s <= i and not win[i - s]:
                w = True
                break
        win[i] = w
    if win[n]:
        for s in moves:
            if s <= n and not win[n - s]:
                return "WIN " + str(s)
    return "LOSE"
