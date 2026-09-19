def solve(text):
    lines = text.splitlines()
    n, k = map(int, lines[0].split())
    steps = sorted(map(int, lines[1].split()))
    # win[i] = True 表示剩 i 颗时轮到当前行动者有必胜策略
    win = [False] * (n + 1)
    best = [None] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                best[i] = s
                break
    if not win[n]:
        return "LOSE"
    return "WIN %d" % best[n]
