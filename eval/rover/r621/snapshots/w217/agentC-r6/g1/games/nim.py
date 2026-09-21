"""Nim：多堆取石子，先手必胜时给出堆号最小者的必胜着法。

约定：solve 返回的字符串末尾不带换行。
"""


def solve(text: str) -> str:
    """text = 完整 stdin 文本；返回 'WIN p r' 或 'LOSE'。"""
    lines = text.split("\n")
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()[:m]]
    x = 0
    for v in piles:
        x ^= v
    if x == 0:
        return "LOSE"
    for idx, v in enumerate(piles):
        target = v ^ x
        if target < v:
            return "WIN %d %d" % (idx + 1, v - target)
    return "LOSE"
