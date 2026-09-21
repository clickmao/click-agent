"""Subtraction game: report the smallest winning first move or LOSE."""


def solve(text: str) -> str:
    lines = text.split("\n")
    n, k = map(int, lines[0].split())
    moves = sorted(int(x) for x in lines[1].split())[:k]

    win = [False] * (n + 1)
    for stones in range(1, n + 1):
        for s in moves:
            if s > stones:
                break
            if not win[stones - s]:
                win[stones] = True
                break

    if not win[n]:
        return "LOSE"
    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
