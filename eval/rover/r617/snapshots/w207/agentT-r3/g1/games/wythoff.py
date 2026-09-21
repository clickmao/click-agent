"""Wythoff 博弈：必败点判定；必胜时给出字典序最小的取胜着法。"""


def _is_lose(a, b):
    if a > b:
        a, b = b, a
    return a == int((b - a) * (1 + 5 ** 0.5) / 2)


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[0:2])
    if _is_lose(a, b):
        return 'LOSE'
    inn = list(range(a + 1))
    jnn = list(range(b + 1))
    for i in inn:
        for j in jnn:
            if i == 0 and j == 0:
                continue
            if i > a or j > b:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _is_lose(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
