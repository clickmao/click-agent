"""Wythoff 博弈: 判定先手胜负并给出字典序最小的必胜着法。"""


def _cold(a, b):
    """冷态 (必败) 判定: 极差等于 floor(phi*min)，等价于枚举。"""
    if a > b:
        a, b = b, a
    return b - a == int(a * ((5 ** 0.5 - 1) / 2 + 1)) - a


def _is_lose(a, b):
    """枚举法判必败点, 避免浮点误差。"""
    if a > b:
        a, b = b, a
    for t in range(0, 40):
        p = int(t * (1 + 5 ** 0.5) / 2)
        q = p + t
        if p > 30 or q > 30:
            break
        if (a, b) == (p, q):
            return True
    return False


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            # 合法着法: 单堆取 / 双堆取等量
            if i > 0 and j > 0 and i != j:
                continue
            if _is_lose(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
