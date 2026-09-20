"""Subtraction game: win/lose and smallest winning first move.

Input layout (whole stdin text):
    n k
    s1 s2 ... sk   (distinct, contains 1)
Output: 'WIN m' or 'LOSE', no trailing newline.
State n is winning iff some allowed s <= n leads to a losing state.
The smallest winning first move m is the smallest allowed s <= n with
n - s losing.
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    if not lines or not lines[0].strip():
        return ''
    n, k = map(int, lines[0].split()[:2])
    steps = sorted(int(x) for x in lines[1].split()[:k])
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in steps:
            if s > x:
                break
            if not win[x - s]:
                win[x] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
