"""Subtraction game: report losing position or minimal winning first move."""


def solve(text: str) -> str:
    lines = text.splitlines()
    n, k = (int(x) for x in lines[0].split())
    steps = [int(x) for x in lines[1].split()]
    steps = sorted(set(steps))
    if 1 in steps:
        steps = [s for s in steps if s >= 1]

    # win[i] = True if the player to move with i stones can force a win
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
