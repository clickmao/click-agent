PHI = (1 + 5 ** 0.5) / 2


def _lose(a, b):
    if a > b:
        a, b = b, a
    idx = int((b - a) / PHI) if b > a else 0
    for t in (idx - 1, idx, idx + 1, idx + 2):
        if t < 0:
            continue
        if a == int(t * PHI) and b == a + t:
            return True
    return False


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    if not _lose(a, b):
        moves = []
        for i in range(a + 1):
            for j in range(b + 1):
                if i == 0 and j == 0:
                    continue
                if not ((i > 0 and j == 0) or (i == 0 and j > 0) or (i == j)):
                    continue
                if _lose(a - i, b - j):
                    moves.append((i, j))
        best = min(moves)
        return 'WIN %d %d' % best
    return 'LOSE'
