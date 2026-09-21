"""多堆 Nim: 给出堆号最小的必胜着法(取走任意正数颗)。

入参为完整 stdin 文本, 返回应当写出的 stdout 文本(末尾不带换行)。
"""


def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(tokens[1 + i]) for i in range(m)]

    x = 0
    for v in piles:
        x ^= v
    if x == 0:
        return "LOSE"

    for idx in range(m):
        target = piles[idx] ^ x
        if target < piles[idx]:
            take = piles[idx] - target
            return "WIN " + str(idx + 1) + " " + str(take)
    return "LOSE"
