def solve(text):
    lines = [ln for ln in text.split('\n') if ln.strip() != '']
    n, k = map(int, lines[0].split())
    S = sorted(map(int, lines[1].split()))
    win = [False] * (n + 1)
    move = [0] * (n + 1)
    for i in range(1, n + 1):
        for s in S:
            if s <= i and not win[i - s]:
                win[i] = True
                move[i] = s
                break
    if win[n]:
        return 'WIN %d' % move[n]
    return 'LOSE'
