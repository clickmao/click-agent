"""Subtraction game: WIN m (smallest winning first move) or LOSE."""


def solve(text: str) -> str:
    lines = text.split('\n')
    it = iter(lines)
    first = next(it).split()
    n, k = int(first[0]), int(first[1])
    moves = [int(t) for t in next(it).split()]
    moves = moves[:k]
    moves = sorted(set(moves))

    # win[i]: current player wins with i stones remaining
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return 'LOSE'
    best = None
    for s in moves:
        if s <= n and not win[n - s]:
            best = s
            break
    return 'WIN ' + str(best)
