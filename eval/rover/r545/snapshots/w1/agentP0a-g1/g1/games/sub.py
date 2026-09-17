def solve(text: str) -> str:
    lines = text.split('\n')
    while lines and lines[0].strip() == '':
        lines.pop(0)
    n, k = map(int, lines[0].split())
    moves = sorted(map(int, lines[1].split()))
    # win[i] = True 表示剩 i 颗时轮到出手的人有必胜策略
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    smallest = None
    for s in moves:
        if s <= n and not win[n - s]:
            smallest = s
            break
    return 'WIN ' + str(smallest)
