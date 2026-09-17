_MAX = 26


def _build_losing():
    losing = set()
    for total in range(0, 2 * _MAX + 1):
        for a in range(0, total + 1):
            b = total - a
            is_lose = not _has_move_to_losing(a, b, losing)
            if is_lose:
                losing.add((a, b))
    return losing


def _has_move_to_losing(a, b, losing):
    for t in range(1, a + 1):
        if (a - t, b) in losing:
            return True
    for t in range(1, b + 1):
        if (a, b - t) in losing:
            return True
    for t in range(1, min(a, b) + 1):
        if (a - t, b - t) in losing:
            return True
    return False


_LOSING = _build_losing()


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if (a - i, b - j) in _LOSING:
                best = (i, j)
                break
        if best is not None:
            break
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
