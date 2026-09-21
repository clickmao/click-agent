def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    s = sorted(int(x) for x in tokens[2:2 + k])
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        w = False
        for step in s:
            if step > i:
                break
            if not win[i - step]:
                w = True
                break
        win[i] = w
    if not win[n]:
        return 'LOSE'
    for step in s:
        if step <= n and not win[n - step]:
            return 'WIN ' + str(step)
    return 'LOSE'
