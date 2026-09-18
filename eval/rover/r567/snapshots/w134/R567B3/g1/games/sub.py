def solve(text: str) -> str:
    data = text.split()
    n = int(data[0])
    k = int(data[1])
    moves = sorted(int(x) for x in data[2:2 + k])
    win = [False] * (n + 1)
    best = [None] * (n + 1)
    for x in range(1, n + 1):
        for s in moves:
            if s <= x and not win[x - s]:
                win[x] = True
                best[x] = s
                break
    if win[n]:
        return "WIN %d" % best[n]
    return "LOSE"
