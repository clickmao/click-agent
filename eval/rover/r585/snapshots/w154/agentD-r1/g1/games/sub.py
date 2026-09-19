def solve(text):
    tok = text.split()
    n = int(tok[0])
    k = int(tok[1])
    moves = [int(x) for x in tok[2:2 + k]]
    # win[i] = True 表示还剩 i 颗时轮到当前行动者有必胜策略
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return "LOSE"
    for s in sorted(moves):
        if s <= n and not win[n - s]:
            return "WIN " + str(s)
    return "LOSE"
