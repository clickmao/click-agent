"""Subtraction game: first player wins iff a move to a losing position exists."""


def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    moves = sorted(int(x) for x in tokens[2:2 + k])

    losing = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and losing[i - s]:
                losing[i] = True
                break

    if losing[n]:
        for s in moves:
            if s <= n and not losing[n - s]:
                return "WIN " + str(s)
    return "LOSE"
