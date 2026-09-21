"""Subtraction game: normal play, last stone wins."""


def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    moves = [int(t) for t in tokens[2:2 + k]]
    win = [False] * (n + 1)
    for total in range(1, n + 1):
        ok = False
        for mv in moves:
            if mv <= total and not win[total - mv]:
                ok = True
                break
        win[total] = ok
    if not win[n]:
        return 'LOSE'
    for mv in sorted(moves):
        if mv <= n and not win[n - mv]:
            return 'WIN %d' % mv
    return 'LOSE'
