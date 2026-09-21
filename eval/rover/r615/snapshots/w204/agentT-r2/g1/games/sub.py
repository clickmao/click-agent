"""Subtraction game: first player win/lose and the smallest winning move."""


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    n, k = (int(x) for x in lines[idx].split()[:2])
    idx += 1
    moves = []
    while len(moves) < k and idx < len(lines):
        moves.extend(int(x) for x in lines[idx].split())
        idx += 1
    moves = moves[:k]

    win = [False] * (n + 1)
    for m in range(1, n + 1):
        for s in moves:
            if s <= m and not win[m - s]:
                win[m] = True
                break

    if not win[n]:
        return "LOSE"
    for s in sorted(moves):
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
