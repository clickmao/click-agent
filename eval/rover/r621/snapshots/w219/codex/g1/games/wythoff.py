from functools import lru_cache


@lru_cache(maxsize=None)
def _win(a: int, b: int) -> bool:
    if a == 0 and b == 0:
        return False
    for i in range(1, a + 1):
        if not _win(a - i, b):
            return True
    for j in range(1, b + 1):
        if not _win(a, b - j):
            return True
    for t in range(1, min(a, b) + 1):
        if not _win(a - t, b - t):
            return True
    return False


def solve(text: str) -> str:
    lines = text.split('\n')
    a, b = map(int, lines[0].split())
    if not _win(a, b):
        return 'LOSE'
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            ma, mb = a - i, b - j
            if ma < 0 or mb < 0:
                continue
            if not _win(ma, mb):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
