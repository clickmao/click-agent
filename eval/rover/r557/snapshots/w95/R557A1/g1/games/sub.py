"""Subtraction game: decide win/lose and the smallest winning first move."""


def solve(text: str) -> str:
    lines = text.split()
    n = int(lines[0])
    _k = int(lines[1])
    moves = sorted(set(int(x) for x in lines[2:2 + _k]))
    moves = [s for s in moves if 1 <= s <= n]

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
