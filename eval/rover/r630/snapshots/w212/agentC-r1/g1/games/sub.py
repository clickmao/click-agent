def solve(text: str) -> str:
    lines = text.splitlines()
    n, k = map(int, lines[0].split())
    moves = sorted(map(int, lines[1].split()))
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for m in moves:
            if m <= x and not win[x - m]:
                win[x] = True
                break
    if not win[n]:
        return "LOSE"
    for m in moves:
        if m <= n and not win[n - m]:
            return "WIN " + str(m)
