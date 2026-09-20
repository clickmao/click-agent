"""Take-away subtraction game: minimal winning first move or LOSE."""


def solve(text: str) -> str:
    lines = text.split()
    n, k = int(lines[0]), int(lines[1])
    steps = sorted(int(x) for x in lines[2:2 + k])

    # window[r] = True if the player to move with r stones wins.
    window = [False] * (n + 1)
    for r in range(1, n + 1):
        for s in steps:
            if s > r:
                break
            if not window[r - s]:
                window[r] = True
                break

    if not window[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not window[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
