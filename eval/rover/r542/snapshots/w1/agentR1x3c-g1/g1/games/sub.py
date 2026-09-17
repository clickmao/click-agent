def _parse(text):
    lines = text.split('\n')
    i = 0
    while i < len(lines) and lines[i].strip() == '':
        i += 1
    n, k = map(int, lines[i].split())
    i += 1
    while i < len(lines) and lines[i].strip() == '':
        i += 1
    moves = list(map(int, lines[i].split()))
    return n, moves


def solve(text):
    n, moves = _parse(text)
    win = [False] * (n + 1)
    for stones in range(1, n + 1):
        w = False
        for s in moves:
            if s <= stones and not win[stones - s]:
                w = True
                break
        win[stones] = w
    if not win[n]:
        return 'LOSE'
    for s in sorted(moves):
        if s <= n and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
