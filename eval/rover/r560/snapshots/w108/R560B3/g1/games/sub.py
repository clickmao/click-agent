def _win(n, moves, cache):
    if n in cache:
        return cache[n]
    res = False
    for s in moves:
        if s <= n and not _win(n - s, moves, cache):
            res = True
            break
    cache[n] = res
    return res


def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n') if ln.strip() != '']
    n, k = map(int, lines[0].split())
    moves = sorted(set(map(int, lines[1].split())))
    cache = {0: False}
    if not _win(n, moves, cache):
        return 'LOSE'
    for s in moves:
        if s <= n and not _win(n - s, moves, cache):
            return 'WIN %d' % s
    return 'LOSE'
