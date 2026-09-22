def _is_lose(i, j):
    if i > j:
        i, j = j, i
    d = j - i
    x = (d * (1 + 5 ** 0.5)) // 2
    return i == x and j == x + d


def _legal(a, b, i, j):
    if i < 0 or j < 0 or i > a or j > b:
        return False
    if i == 0 and j == 0:
        return False
    return i == 0 or j == 0 or i == j


def solve(text: str) -> str:
    a, b = map(int, text.split()[0:2])
    if _is_lose(a, b):
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if not _legal(a, b, i, j):
                continue
            if _is_lose(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
