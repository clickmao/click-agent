"""Wythoff 博弈：必败点判定与字典序最小的必胜着法。"""


def solve(text: str) -> str:
    lines = text.split("\n")
    first = lines[0].split()
    a, b = int(first[0]), int(first[1])

    def is_lose(x: int, y: int) -> bool:
        lo, hi = min(x, y), max(x, y)
        d = hi - lo
        # 必败点: lo == floor(d * phi)
        lo_expected = (d * 1618033988749895) // 1000000000000000
        return lo == lo_expected

    if is_lose(a, b):
        return "LOSE"
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if is_lose(na, nb):
                return "WIN " + str(i) + " " + str(j)
    return "LOSE"
