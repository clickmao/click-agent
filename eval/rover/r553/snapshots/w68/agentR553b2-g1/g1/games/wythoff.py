"""Wythoff 博弈：必胜着法按 (i, j) 字典序最小（先比 i 再比 j）。

i = 从第一堆取走数, j = 从第二堆取走数。合法着法:
  (i) 只动一堆: (t, 0) 或 (0, t), t >= 1
  (ii) 两堆同取: (t, t), t >= 1
着法后局面为必败点则当前为必胜。"""


def _lose_positions(limit):
    lose = set()
    for a in range(limit + 1):
        for b in range(limit + 1):
            if _is_lose(a, b, lose):
                lose.add((a, b))
    return lose


def _is_lose(a, b, lose):
    if (a, b) in lose:
        return True
    keys = frozenset(((a, b), (b, a)))
    for (x, y) in lose:
        if frozenset(((x, y), (y, x))) == keys:
            return True
    for t in range(1, min(a, b) + 1):
        if _pair_in((a - t, b - t), lose):
            return False
    for t in range(1, a + 1):
        if _pair_in((a - t, b), lose):
            return False
    for t in range(1, b + 1):
        if _pair_in((a, b - t), lose):
            return False
    return True


def _pair_in(pair, lose):
    return pair in lose or (pair[1], pair[0]) in lose


def solve(text: str) -> str:
    toks = text.split()
    a, b = int(toks[0]), int(toks[1])
    lose = _lose_positions(25)
    if _pair_in((a, b), lose):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            ok = False
            if i > 0 and j == 0:
                ok = True
            elif i == 0 and j > 0:
                ok = True
            elif i == j:
                ok = True
            if not ok:
                continue
            if _pair_in((a - i, b - j), lose):
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN %d %d' % best
