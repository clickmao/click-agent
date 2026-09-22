"""Take-away game: decide win/lose from position n with allowed moves."""


def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = map(int, lines[0].split()[:2])
    moves = [int(x) for x in lines[1].split()[:k]]
    moves = sorted(set(moves))

    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
