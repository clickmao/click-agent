def solve(text: str) -> str:
    parts = text.split()
    n = int(parts[0])
    k = int(parts[1])
    moves = [int(x) for x in parts[2:2 + k]]
    winning = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not winning[i - s]:
                winning[i] = True
                break
    if not winning[n]:
        return 'LOSE'
    for s in sorted(moves):
        if s <= n and not winning[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
