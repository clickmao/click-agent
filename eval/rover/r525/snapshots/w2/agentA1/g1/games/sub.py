"""Subtraction game: report the minimal winning first move, or LOSE.

solve(text) is pure: text is the complete stdin, the return value is the
complete stdout (no trailing newline).
"""


def solve(text: str) -> str:
    tokens = text.split()
    if not tokens:
        return ""

    n = int(tokens[0])
    k = int(tokens[1])
    moves = [int(x) for x in tokens[2:2 + k]]

    # win[i] = True iff the player to move with i stones has a winning strategy.
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"

    for s in sorted(moves):
        if s <= n and not win[n - s]:
            return "WIN %d" % s

    # Unreachable when win[n] is True, kept as a defensive fallback.
    return "LOSE"
