"""Subtraction game: who wins and the smallest winning first move."""


def solve(text: str) -> str:
    tokens = text.split()
    pos = 0
    n = int(tokens[pos]); pos += 1
    k = int(tokens[pos]); pos += 1
    moves = sorted(int(tokens[pos + i]) for i in range(k))

    # win[x] = True if the player to move with x stones wins
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
            return 'WIN ' + str(s)
    return 'LOSE'
