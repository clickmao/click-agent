"""Wythoff 博弈: 判定必败点, 否则给出字典序最小的必胜着法。

输入: 一行两个整数 a b (两堆石子数)。
每次可 (i) 从一堆取任意正数, 或 (ii) 从两堆取相同正数; 取最后一颗者胜。
输出: 必败 -> "LOSE"; 否则 -> "WIN i j" ((i,j) 在全部必胜着法中字典序最小)。
"""

MAXN = 200


def _losing_pairs():
    """构造 Wythoff 必败点集合中的 (a,b) 对, a<=b; 用于查表。"""
    pairs = set()
    used = set()
    # (0,0) 是必败点, 但输入 a,b>=1, 不需要, 仍纳入判断
    pairs.add((0, 0))
    an, bn = 0, 0
    phi = (1 + 5 ** 0.5) / 2
    for n in range(1, 200):
        an = int(n * phi)
        bn = an + n
        if bn > MAXN:
            break
        pairs.add((an, bn))
    return pairs


_LOSING = _losing_pairs()


def _is_losing(a: int, b: int) -> bool:
    lo, hi = (a, b) if a <= b else (b, a)
    return (lo, hi) in _LOSING


def solve(text: str) -> str:
    lines = [ln for ln in text.split("\n") if ln.strip() != ""]
    a, b = (int(x) for x in lines[0].split()[:2])

    if _is_losing(a, b):
        return "LOSE"

    # 枚举所有合法着法, 找结果为必败点的着法, 按 (i,j) 字典序最小
    best = None
    # (i) 从第一堆取 i
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            # 合法着法: 只从一堆取 (i>0,j==0) 或 (i==0,j>0); 或两堆取相同 (i==j>0)
            if not ((i > 0 and j == 0) or (i == 0 and j > 0) or (i == j and i > 0)):
                continue
            ra, rb = a - i, b - j
            if _is_losing(ra, rb):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
