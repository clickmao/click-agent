"""Subtraction game: decide win/lose and the smallest winning first move."""


def solve(text: str) -> str:
    lines = text.split("\n")
    first = lines[0].split()
    n, k = int(first[0]), int(first[1])
    moves = [int(x) for x in lines[1].split()[:k]]
    moves.sort()

    win = [False] * (n + 1)
    for stones in range(1, n + 1):
        for take in moves:
            if take > stones:
                break
            if not win[stones - take]:
                win[stones] = True
                break

    for take in moves:
        if take <= n and not win[n - take]:
            return "WIN %d" % take
    return "LOSE"
