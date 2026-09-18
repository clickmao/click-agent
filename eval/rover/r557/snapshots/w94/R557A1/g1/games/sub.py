"""Take-away game: win/lose plus smallest winning first move."""


def solve(text: str) -> str:
    lines = text.splitlines()
    n, k = (int(x) for x in lines[0].split()[:2])
    steps = [int(x) for x in lines[1].split()[:k]]

    win = [False] * (n + 1)
    for stones in range(1, n + 1):
        for s in steps:
            if s <= stones and not win[stones - s]:
                win[stones] = True
                break

    if not win[n]:
        return 'LOSE'
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
