def solve(text: str) -> str:
    lines = text.split('\n')
    while lines and lines[0].strip() == '':
        lines.pop(0)
    if not lines:
        return ''
    n, k = map(int, lines[0].split())
    nums = []
    if 1 < len(lines):
        nums = list(map(int, lines[1].split()))
    moves = sorted(set(nums))
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        ok = False
        for s in moves:
            if s <= x and not win[x - s]:
                ok = True
                break
        win[x] = ok
    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
