def solve(text: str) -> str:
    lines = text.splitlines()
    n, k = map(int, lines[0].split())
    moves = sorted(map(int, lines[1].split()))
    win = [False] * (n + 1)
    best = [0] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                best[i] = s
                break
    if win[n]:
        return 'WIN ' + str(best[n])
    return 'LOSE'
