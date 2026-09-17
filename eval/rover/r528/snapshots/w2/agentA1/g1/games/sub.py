"""Subtraction game: report the smallest winning first move, or LOSE."""


def solve(text: str) -> str:
    """n stones, allowed moves s1..sk (contains 1); last stone taken wins."""
    lines = text.splitlines()
    n, k = (int(v) for v in lines[0].split()[:2])
    moves = sorted(int(v) for v in lines[1].split()[:k])

    # win[i] == True  -> the player to move with i stones has a winning strategy.
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        win[i] = any(s <= i and not win[i - s] for s in moves)

    if not win[n]:
        return 'LOSE'
    best = None
    for s in moves:  # moves ascending -> first match is the smallest winning move
        if s <= n and not win[n - s]:
            best = s
            break
    return 'WIN %d' % best
