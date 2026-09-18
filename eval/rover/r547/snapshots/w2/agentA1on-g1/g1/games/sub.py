"""Subtraction game: last stone taken wins (normal play)."""


def solve(text: str) -> str:
    lines = text.splitlines()
    n, k = (int(x) for x in lines[0].split())
    moves = sorted(int(x) for x in lines[1].split()[:k])

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
        return 'LOSE'
    for s in moves:  # ascending -> smallest winning first move
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
