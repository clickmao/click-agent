"""Subtraction game: determine win/lose and the smallest winning move."""


def solve(text: str) -> str:
    parts = text.split()
    idx = 0
    n = int(parts[idx]); idx += 1
    k = int(parts[idx]); idx += 1
    moves = [int(parts[idx + t]) for t in range(k)]
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in sorted(moves):
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
