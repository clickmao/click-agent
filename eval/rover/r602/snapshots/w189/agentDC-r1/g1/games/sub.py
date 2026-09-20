"""Subtraction game: report smallest winning first move, or LOSE."""


def solve(text: str) -> str:
    data = text.split()
    n = int(data[0])
    k = int(data[1])
    steps = [int(x) for x in data[2:2 + k]]
    steps = sorted(set(s for s in steps if s >= 1))

    win = [False] * (n + 1)
    for i in range(1, n + 1):
        w = False
        for s in steps:
            if s > i:
                break
            if not win[i - s]:
                w = True
                break
        win[i] = w

    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
