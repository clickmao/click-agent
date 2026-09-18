def solve(text: str) -> str:
    lines = text.split(chr(10))
    n, k = map(int, lines[0].split())
    s = sorted(map(int, lines[1].split()))
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
