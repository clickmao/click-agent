"""Nim 多堆游戏：给出堆号最小、取走数唯一的必胜着法。"""


def solve(text: str) -> str:
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()[:m]]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    for idx, a in enumerate(piles, start=1):
        t = a ^ x
        if t < a:
            return "WIN %d %d" % (idx, a - t)
    return "LOSE"
