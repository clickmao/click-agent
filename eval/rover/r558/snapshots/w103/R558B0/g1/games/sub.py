"""Game: subtraction game (take exactly one of the allowed amounts; last stone wins)."""


def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n') if ln.strip() != '']
    n, k = (int(x) for x in lines[0].split())
    steps = [int(x) for x in lines[1].split()][:k]

    win = [False] * (n + 1)
    for total in range(1, n + 1):
        for s in steps:
            if s <= total and not win[total - s]:
                win[total] = True
                break

    if not win[n]:
        return 'LOSE'
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
