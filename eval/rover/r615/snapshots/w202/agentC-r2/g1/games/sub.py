"""Subtraction game: first player's win/lose and smallest winning first move."""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    n, k = (int(x) for x in lines[idx].split())
    idx += 1
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    s = [int(x) for x in lines[idx].split()]
    moves = sorted(s)
    winning = [False] * (n + 1)
    for i in range(1, n + 1):
        for mv in moves:
            if mv > i:
                break
            if not winning[i - mv]:
                winning[i] = True
                break
    if not winning[n]:
        return 'LOSE'
    for mv in moves:
        if mv <= n and not winning[n - mv]:
            return 'WIN %d' % mv
    return 'LOSE'
