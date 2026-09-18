def solve(text: str) -> str:
    lines = text.splitlines()
    n, k = (int(x) for x in lines[0].split())
    moves = [int(x) for x in lines[1].split()][:k]
    moves.sort()

    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for mv in moves:
            if mv <= i and not win[i - mv]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    for mv in moves:
        if mv <= n and not win[n - mv]:
            return "WIN %d" % mv
    return "LOSE"
