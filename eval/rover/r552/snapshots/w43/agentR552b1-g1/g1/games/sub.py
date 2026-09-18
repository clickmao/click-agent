def _win(n, moves, memo):
    if n == 0:
        return False
    if n in memo:
        return memo[n]
    res = False
    for s in moves:
        if s <= n and not _win(n - s, moves, memo):
            res = True
            break
    memo[n] = res
    return res


def solve(text):
    data = text.split()
    idx = 0
    n = int(data[idx]); idx += 1
    k = int(data[idx]); idx += 1
    moves = sorted(int(data[idx + i]) for i in range(k))
    memo = {}
    if not _win(n, moves, memo):
        return 'LOSE'
    for s in moves:
        if s <= n and not _win(n - s, moves, memo):
            return 'WIN ' + str(s)
    return 'LOSE'
