"""Subtraction game: n k / s1..sk (contains 1). WIN m with smallest winning first take, else LOSE."""


def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n')]
    if lines and lines[-1] == '':
        lines.pop()
    n, k = map(int, lines[0].split())
    moves = sorted(int(x) for x in lines[1].split())
    win = [False] * (n + 1)
    first = [None] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                first[i] = s
                break
    if win[n]:
        return 'WIN %d' % first[n]
    return 'LOSE'
