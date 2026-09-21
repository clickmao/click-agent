"""多堆 Nim: 必胜手(堆号最小、每堆至多一个必胜着法)。

约定: text 为该游戏的完整 stdin 文本; 返回应当写出的 stdout 文本, 末尾不带换行。
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    if not lines:
        return ''
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for idx, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return 'WIN %d %d' % (idx + 1, a - target)
    return 'LOSE'
