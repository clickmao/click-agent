"""Subtraction game: who wins taking exactly one of allowed amounts.

stdin:
    first line: n k
    second line: k distinct amounts s1..sk (contain 1)
stdout: 'WIN m' with smallest winning first move, or 'LOSE'.
Pure function: solve(text) -> str (no trailing newline).
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    n, k = (int(x) for x in lines[0].split())
    steps = [int(x) for x in lines[1].split()][:k]

    # win[i] = True if the player to move with i stones has a winning strategy.
    win = [False] * (n + 1)
    best = [-1] * (n + 1)
    for i in range(1, n + 1):
        for s in sorted(steps):
            if s <= i and not win[i - s]:
                win[i] = True
                best[i] = s
                break  # sorted -> first found is the numerically smallest

    if not win[n]:
        return 'LOSE'
    return 'WIN %d' % best[n]
