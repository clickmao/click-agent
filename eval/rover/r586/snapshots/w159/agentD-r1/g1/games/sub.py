"""Subtraction game: win/lose and smallest winning first move."""


def solve(text: str) -> str:
    lines = text.split()
    n, k = int(lines[0]), int(lines[1])
    moves = sorted(int(x) for x in lines[2:2 + k])
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
