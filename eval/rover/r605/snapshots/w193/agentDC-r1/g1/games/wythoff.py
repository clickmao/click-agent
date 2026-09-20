"""Wythoff's game: losing positions and lexicographically smallest winning move."""


def is_losing(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    j = b - a
    ak = (5 ** 0.5) * j
    ak = (ak + j) / 2.0
    ai = int(ak + 0.5)
    while ai > 0 and (ai * ai - ai * 0 + 0) > 0 and ai - (ai * ai + ai) // 2 > j:
        ai -= 1
    # exact check against the Wythoff pair for index ai
    for cand in (ai - 1, ai, ai + 1):
        if cand < 0:
            continue
        x = (cand * (1 + 5 ** 0.5)) / 2.0
        x = int(x + 0.5)
        y = x + cand
        if x == a and y == b:
            return True
    return False


def _losing_pair_upto(limit: int):
    pairs = set()
    used = set()
    j = 0
    while True:
        x = int(j * (1 + 5 ** 0.5) / 2.0 + 0.5)
        while x in used:
            x += 1
        y = x + j
        if x > limit and y > limit:
            break
        used.add(x)
        used.add(y)
        pairs.add((x, y))
        j += 1
        if j > 4 * limit + 10:
            break
    return pairs


def solve(text: str) -> str:
    toks = text.split()
    a = int(toks[0])
    b = int(toks[1])

    losing = _losing_pair_upto(max(a, b) + 2)
    if (min(a, b), max(a, b)) in losing:
        return "LOSE"

    best = None
    # move (i, j) with i from pile 1, j from pile 2; lexicographic by (i, j)
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if na < 0 or nb < 0:
                continue
            if (min(na, nb), max(na, nb)) in losing:
                best = (i, j)
                break
        if best is not None:
            break
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
