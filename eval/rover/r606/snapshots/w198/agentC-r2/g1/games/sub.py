"""Subtraction game: smallest winning first move or LOSE."""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    n, k = map(int, lines[idx].split())
    idx += 1
    moves = []
    while len(moves) < k and idx < len(lines):
        moves.extend(int(tok) for tok in lines[idx].split())
        idx += 1
    moves = moves[:k]

    win = [False] * (n + 1)
    for t in range(1, n + 1):
        for s in moves:
            if s <= t and not win[t - s]:
                win[t] = True
                break

    if win[n]:
        for s in sorted(moves):
            if s <= n and not win[n - s]:
                return 'WIN ' + str(s)
        return 'LOSE'
    return 'LOSE'
