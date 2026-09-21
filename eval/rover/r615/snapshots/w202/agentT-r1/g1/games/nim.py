"""多堆 Nim: 给出堆号最小必胜着法。"""


def solve(text: str) -> str:
    """输入完整 stdin 文本, 返回应写出的 stdout 文本(末尾不带换行)。"""
    lines = text.splitlines()
    if not lines:
        return ""
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    for idx, a in enumerate(piles):
        target = a ^ x
        if target < a:
            take = a - target
            return "WIN %d %d" % (idx + 1, take)
    return "LOSE"
