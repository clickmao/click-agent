"""Subtraction game: first player win/lose and smallest winning move."""


def solve(text: str) -> str:
    data = text.split()
    n = int(data[0])
    k = int(data[1])
    steps = sorted(int(x) for x in data[2:2 + k])

    lose = [False] * (n + 1)
    lose[0] = True
    for i in range(1, n + 1):
        lost = True
        for s in steps:
            if s <= i and lose[i - s]:
                lost = False
                break
        lose[i] = lost

    if lose[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and lose[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
