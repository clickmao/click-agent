def solve(text: str) -> str:
    lines = text.split("\n")
    n, k = map(int, lines[0].split())
    moves = sorted(map(int, lines[1].split()))[:k]
    win = [False] * (n + 1)
    for stones in range(1, n + 1):
        for mv in moves:
            if mv <= stones and not win[stones - mv]:
                win[stones] = True
                break
    if not win[n]:
        return "LOSE"
    for mv in moves:
        if mv <= n and not win[n - mv]:
            return "WIN " + str(mv)
    return "LOSE"
