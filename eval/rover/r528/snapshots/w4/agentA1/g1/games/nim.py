"""多堆 Nim: 给出堆号最小且必胜的着法。"""


def solve(text: str) -> str:
    data = text.split()
    m = int(data[0])
    piles = [int(x) for x in data[1:1 + m]]

    x = 0
    for a in piles:
        x ^= a

    if x == 0:
        return "LOSE"

    # 堆号最小者: 找到使该堆变为 a ^ x 的堆 (a ^ x < a 即必胜)
    for idx in range(m):
        a = piles[idx]
        target = a ^ x
        if target < a:
            return "WIN " + str(idx + 1) + " " + str(a - target)
    return "LOSE"
