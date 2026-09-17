"""Subtraction game: report the winning first move (smallest) or LOSE."""


def solve(text: str) -> str:
    lines = text.splitlines()
    n, _k = map(int, lines[0].split())
    moves = sorted(set(int(v) for v in lines[1].split()))

    # win[i] = True iff the player to move with i stones can force a win.
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"  # unreachable given win[n] is True
