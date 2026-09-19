def solve(text):
    tokens = text.split()
    pos = 0
    n = int(tokens[pos]); pos += 1
    k = int(tokens[pos]); pos += 1
    s = [int(tokens[pos + i]) for i in range(k)]

    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for move in s:
            if move <= i and not win[i - move]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    best = None
    for move in sorted(s):
        if move <= n and not win[n - move]:
            best = move
            break
    return "WIN " + str(best)
