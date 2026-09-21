"""Subtraction game: computed over n stones in O(n)."""


def solve(text):
    lines = text.split('\n')
    first = lines[0].split()
    n = int(first[0])
    k = int(first[1])
    moves = sorted(int(x) for x in lines[1].split())
    moves = [x for x in moves if x <= n]
    win = [False] * (n + 1)
    move = [-1] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                move[i] = s
                break
    if not win[n]:
        return 'LOSE'
    return 'WIN %d' % move[n]
