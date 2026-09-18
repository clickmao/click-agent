def solve(text: str) -> str:
    lines = text.split("\n")
    n, k = map(int, lines[0].split())
    moves = list(map(int, lines[1].split()))
    moves.sort()

    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for m in moves:
            if m > i:
                break
            if not win[i - m]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    for m in moves:
        if m <= n and not win[n - m]:
            return "WIN %d" % m
    return "LOSE"
