"""多堆 Nim：必胜手（堆号最小者的唯一取法）。

输入格式：
第一行一个整数 m (1<=m<=4)
第二行 m 个整数 a1..am (1<=ai<=15)

输出：
先手必胜 -> 'WIN p r'（p 为堆号最小的必胜着法所用堆号，从 1 开始；r 为从该堆取走数）
先手必败 -> 'LOSE'
solve 返回值末尾不带换行。
"""


def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n') if ln.strip() != '']
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i, a in enumerate(piles):
        b = a ^ x
        if b < a:
            return 'WIN %d %d' % (i + 1, a - b)
    return 'LOSE'
