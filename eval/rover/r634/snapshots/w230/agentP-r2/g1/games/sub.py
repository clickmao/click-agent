def solve(text: str) -> str:
    lines = text.split('\n')
    first = lines[0].split()
    n = int(first[0])
    k = int(first[1])
    moves = sorted(int(x) for x in lines[1].split()[:k])
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if win[n]:
        for s in moves:
            if s <= n and not win[n - s]:
                return 'WIN %d' % s
    return 'LOSE'
