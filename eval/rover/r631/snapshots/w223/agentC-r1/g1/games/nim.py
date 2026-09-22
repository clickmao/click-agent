"""多堆 Nim：必胜手。

入参 text 为完整 stdin 文本，返回应当写出的 stdout 文本（末尾不带换行）。
"""


def solve(text: str) -> str:
    tok = text.split()
    m = int(tok[0])
    a = [int(x) for x in tok[1:1 + m]]

    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return 'LOSE'

    for p in range(m):
        target = a[p] ^ x
        if target < a[p]:
            return 'WIN %d %d' % (p + 1, a[p] - target)
    return 'LOSE'
