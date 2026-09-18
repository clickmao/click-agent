def solve(text: str) -> str:
    data = text.split()
    n = int(data[0])
    k = int(data[1])
    moves = [int(x) for x in data[2:2 + k]]

    win = [False] * (n + 1)
    for m in range(1, n + 1):
        for s in moves:
            if s <= m and not win[m - s]:
                win[m] = True
                break

    if not win[n]:
        return "LOSE"
    for s in sorted(moves):
        if s <= n and not win[n - s]:
            return "WIN %d" % s
