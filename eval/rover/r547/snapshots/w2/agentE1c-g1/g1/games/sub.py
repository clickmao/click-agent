"""Subtraction game: WIN with smallest winning move, or LOSE."""


def solve(text: str) -> str:
    lines = text.split('\n')
    if not lines or lines[0].strip() == '':
        return ''
    n, k = map(int, lines[0].split())
    moves = sorted(int(x) for x in lines[1].split())[:k]
    win = [False] * (n + 1)
    for t in range(1, n + 1):
        for s in moves:
            if s <= t and not win[t - s]:
                win[t] = True
                break
    if win[n]:
        for s in moves:
            if s <= n and not win[n - s]:
                return 'WIN ' + str(s)
    return 'LOSE'
