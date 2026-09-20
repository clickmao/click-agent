def solve(text: str) -> str:
    lines = text.split("\n")
    n, k = (int(x) for x in lines[0].split())
    moves = sorted(int(x) for x in lines[1].split())[:k]
    lose = [False] * (n + 1)
    lose[0] = True
    for i in range(1, n + 1):
        win = False
        for s in moves:
            if s <= i and lose[i - s]:
                win = True
                break
        lose[i] = not win
    if lose[n]:
        return "LOSE"
    for s in moves:
        if s <= n and lose[n - s]:
            return "WIN %d" % s
    return "LOSE"
