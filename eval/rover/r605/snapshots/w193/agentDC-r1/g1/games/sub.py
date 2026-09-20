"""Subtraction game: first-player outcome and smallest winning move."""


def solve(text: str) -> str:
    toks = text.split()
    n = int(toks[0])
    k = int(toks[1])
    moves = sorted(int(x) for x in toks[2:2 + k])

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
