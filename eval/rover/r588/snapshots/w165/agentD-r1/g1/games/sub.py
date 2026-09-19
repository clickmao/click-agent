"""Subtraction game: n k then k distinct moves; output 'WIN m' (smallest winning move) or 'LOSE'."""


def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    s = [int(x) for x in tokens[2:2 + k]]
    s = sorted(set(s))

    win = [False] * (n + 1)
    for m in range(1, n + 1):
        for take in s:
            if take <= m and not win[m - take]:
                win[m] = True
                break

    if not win[n]:
        return "LOSE"
    for take in s:
        if take <= n and not win[n - take]:
            return "WIN " + str(take)
    return "LOSE"
