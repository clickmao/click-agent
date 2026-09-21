"""多堆 Nim: 给出堆号最小 (同堆唯一) 的必胜着法。

solve(text) 读入:
  第一行一个整数 m
  第二行 m 个整数 a1..am
规则: 每次从某一堆取走任意正数目的石子, 取走最后一颗者胜。
返回: 'WIN p r' 或 'LOSE'。
"""


def solve(text: str) -> str:
    data = text.split()
    m = int(data[0])
    a = [int(x) for x in data[1:1 + m]]

    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return 'LOSE'
    for i, v in enumerate(a):
        target = v ^ x
        if target < v:
            return 'WIN %d %d' % (i + 1, v - target)
    return 'LOSE'
