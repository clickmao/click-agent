"""Subtraction game: decide first-player win and smallest winning move."""


def solve(text: str) -> str:
    lines = text.split("\n")
    first = lines[0].split()
    n, k = int(first[0]), int(first[1])
    moves = [int(x) for x in lines[1].split()]
    moves = sorted(set(moves))
    win = [False] * (n + 1)
    for j in range(1, n + 1):
        w = False
        for s in moves:
            if s <= j and not win[j - s]:
                w = True
                break
        win[j] = w
    if not win[n]:
        return "LOSE"
    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
