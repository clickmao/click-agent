def solve(text: str) -> str:
    a, b = map(int, text.split())
    moves = []
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            moves.append((i, j))
    moves.sort()

    from functools import lru_cache

    @lru_cache(maxsize=None)
    def win(x, y):
        for i, j in moves:
            if i <= x and j <= y and not win(x - i, y - j):
                return True
        return False

    if not win(a, b):
        return 'LOSE'
    for i, j in moves:
        if i <= a and j <= b and not win(a - i, b - j):
            return 'WIN %d %d' % (i, j)
    return 'LOSE'
