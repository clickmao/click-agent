"""Subtraction game: first player win/lose and minimal winning move."""


def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    moves = [int(tokens[2 + i]) for i in range(k)]
    moves_sorted = sorted(set(moves))

    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves_sorted:
            if s <= i and not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    for s in moves_sorted:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
