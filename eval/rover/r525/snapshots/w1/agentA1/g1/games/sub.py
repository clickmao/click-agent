"""Subtraction game: win/lose + smallest winning first move."""


def solve(text: str) -> str:
    tokens = []
    for line in text.split("\n"):
        tokens.extend(line.split())
    it = iter(tokens)
    n = int(next(it))
    k = int(next(it))
    moves = sorted({int(next(it)) for _ in range(k)})

    # win[p] = True if position with p stones is winning for player to move
    win = [False] * (n + 1)
    for p in range(1, n + 1):
        for s in moves:
            if s <= p and not win[p - s]:
                win[p] = True
                break

    if not win[n]:
        return "LOSE"
    # smallest winning first move
    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
