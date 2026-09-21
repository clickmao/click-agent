"""Subtraction game: last player to take a stone wins."""


def solve(text: str) -> str:
    lines = text.split()
    n = int(lines[0])
    k = int(lines[1])
    moves = sorted(int(v) for v in lines[2:2 + k])

    win = [False] * (n + 1)
    for total in range(1, n + 1):
        for s in moves:
            if s > total:
                break
            if not win[total - s]:
                win[total] = True
                break

    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
