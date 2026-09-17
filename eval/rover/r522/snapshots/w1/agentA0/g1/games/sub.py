"""Subtraction game: last stone wins. Compute smallest winning first move."""


def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = map(int, lines[0].split())
    moves = list(map(int, lines[1].split()))[:k]

    # win[i] = True if player to move with i stones wins
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
