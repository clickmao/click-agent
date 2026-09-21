def _is_lose(a: int, b: int, limit: int) -> bool:
    # Wythoff 必败点 (Beatty 序列): (floor(n*phi), floor(n*phi)+n) 及其对称
    phi = (1 + 5 ** 0.5) / 2
    lo, hi = min(a, b), max(a, b)
    n = (int(lo / phi) + 5) // 1
    for cand in range(max(0, int(lo / phi) - 5), int(lo / phi) + 6):
        an = int(cand * phi)
        if an > limit:
            break
        bn = an + cand
        if (lo, hi) == (an, bn):
            return True
    # 退化点 (0,0)
    return lo == 0 and hi == 0


def solve(text: str) -> str:
    toks = text.split()
    a, b = int(toks[0]), int(toks[1])
    limit = max(a, b) + 1
    # 枚举所有可达状态，标准 Wythoff 必败集判定
    lose = set()
    phi = (1 + 5 ** 0.5) / 2
    n = 0
    while True:
        an = int(n * phi)
        bn = an + n
        if an > limit and bn > limit:
            break
        if an <= limit or bn <= limit:
            lose.add((an, bn))
            lose.add((bn, an))
        n += 1
    lose.add((0, 0))
    if (a, b) in lose:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if (a - i, b - j) in lose:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
