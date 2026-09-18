def solve(text: str) -> str:
    lines = text.split()
    n = int(lines[0])
    k = int(lines[1])
    moves = [int(x) for x in lines[2:2 + k]]
    moves.sort()
    win = [False] * (n + 1)
    best = [0] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                best[i] = s
                break
    if win[n]:
        return 'WIN %d' % best[n]
    return 'LOSE'
