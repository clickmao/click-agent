"""Subtraction game: determine win/lose and smallest winning move."""


def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    moves = sorted(int(t) for t in tokens[2:2 + k])

    winning = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s > i:
                break
            if not winning[i - s]:
                winning[i] = True
                break

    if not winning[n]:
        return "LOSE"
    for s in moves:
        if s <= n and not winning[n - s]:
            return "WIN %d" % s
    return "LOSE"
