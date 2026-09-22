def solve(text):
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    moves = [int(x) for x in tokens[2:2 + k]]
    loses = [False] * (n + 1)
    loses[0] = True
    for total in range(1, n + 1):
        can_win = False
        for s in moves:
            if s <= total and loses[total - s]:
                can_win = True
                break
        loses[total] = not can_win
    if loses[n]:
        return 'LOSE'
    for s in sorted(moves):
        if s <= n and loses[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
