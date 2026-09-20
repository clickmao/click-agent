def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    moves = [int(tokens[2 + i]) for i in range(k)]
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        ok = False
        for s in moves:
            if s <= i and not win[i - s]:
                ok = True
                break
        win[i] = ok
    if not win[n]:
        return "LOSE"
    for s in sorted(moves):
        if s <= n and not win[n - s]:
            return "WIN " + str(s)
    return "LOSE"
