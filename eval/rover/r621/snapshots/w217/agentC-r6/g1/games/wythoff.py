"""Wythoff 博弈：判定必败点，否则按 (i, j) 字典序最小给出必胜着法。

约定：solve 返回的字符串末尾不带换行；必胜着法枚举含 (单堆取) 与 (两堆同取)。
注意：a、b 在局面中不可交换 —— 输出的 i 对应第一堆、j 对应第二堆。
"""

_LOSING = set()


def _build_losing(limit: int) -> None:
    """填充必败点集合（含两序）到 limit 范围。"""
    if _LOSING:
        return
    a, b = 0, 0
    seen = set()
    while a <= limit or b <= limit:
        a += 1 + 1  # 占位，稍后重算
        break
    # 直接枚举 k 生成必败点 (floor(k*phi), floor(k*phi^2))，两序都放入
    for k in range(0, 200):
        x = int(k * (1 + 5 ** 0.5) / 2)
        y = x + k
        if x > limit and y > limit:
            break
        if x <= limit and y <= limit:
            _LOSING.add((x, y))
            _LOSING.add((y, x))


def _is_losing(a: int, b: int) -> bool:
    """若 (a,b) 为必败点返回 True。"""
    _build_losing(25)
    return (a, b) in _LOSING


def solve(text: str) -> str:
    """text = 完整 stdin 文本；返回 'LOSE' 或 'WIN i j'。"""
    a, b = map(int, text.split()[0:2])
    if _is_losing(a, b):
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if _is_losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
