"""Subtraction game: win/lose plus the smallest winning first move."""


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    head = lines[idx].split()
    idx += 1
    n, k = int(head[0]), int(head[1])
    moves = []
    while len(moves) < k and idx < len(lines):
        moves.extend(int(t) for t in lines[idx].split())
        idx += 1
    moves = sorted(set(moves))

    # win[x] = True if the player to move with x stones wins.
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in moves:
            if s > x:
                break
            if not win[x - s]:
                win[x] = True
                break

    if not win[n]:
        return "LOSE"
    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
