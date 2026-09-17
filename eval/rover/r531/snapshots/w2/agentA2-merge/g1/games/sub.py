"""Subtraction game (take-away): normal play, last-stone wins.

Input text format:
    line 1: n k
    line 2: k distinct allowed moves s1..sk (contains 1)

solve(text) -> 'WIN m' (m = smallest winning first move) or 'LOSE'.
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    n, _k = (int(x) for x in lines[idx].split())
    idx += 1
    moves = []
    while idx < len(lines) and not moves:
        moves = [int(x) for x in lines[idx].split()]
        idx += 1
    moves = sorted(set(moves))

    win = [False] * (n + 1)          # win[i]: mover with i stones wins?
    for i in range(1, n + 1):
        for s in moves:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'


if __name__ == '__main__':
    import sys
    sys.stdout.write(solve(sys.stdin.read()))
