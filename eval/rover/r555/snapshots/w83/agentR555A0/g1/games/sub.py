"""Subtraction game: report WIN m (smallest winning move) or LOSE."""


def solve(text):
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    n, k = (int(x) for x in lines[0].split())
    moves = [int(x) for x in lines[1].split()]
    win = [False] * (n + 1)
    for t in range(1, n + 1):
        for s in moves:
            if s <= t and not win[t - s]:
                win[t] = True
                break
    if not win[n]:
        return 'LOSE'
    smallest = None
    for s in sorted(moves):
        if s <= n and not win[n - s]:
            smallest = s
            break
    return 'WIN ' + str(smallest)
