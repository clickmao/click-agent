"""Subtraction game: win/lose plus minimal winning first move."""


def solve(text: str) -> str:
    toks = text.split()
    pos = 0
    n = int(toks[pos]); pos += 1
    k = int(toks[pos]); pos += 1
    moves = []
    for _ in range(k):
        moves.append(int(toks[pos])); pos += 1
    moves = sorted(set(moves))

    # win[x] = True if the player to move with x stones can force a win.
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in moves:
            if s > x:
                break
            if not win[x - s]:
                win[x] = True
                break

    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
