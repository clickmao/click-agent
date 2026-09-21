def solve(text):
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    n, k = map(int, lines[idx].split())
    idx += 1
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    s = sorted(set(int(x) for x in lines[idx].split()))
    s = [x for x in s if 1 <= x <= n]
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for step in s:
            if step <= i and not win[i - step]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for step in s:
        if step <= n and not win[n - step]:
            return 'WIN ' + str(step)
    return 'LOSE'
