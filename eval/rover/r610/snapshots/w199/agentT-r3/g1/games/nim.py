"""多堆 Nim：堆号最小的必胜着法。"""


def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(tokens[1 + i]) for i in range(m)]

    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return "LOSE"
    for idx in range(m):
        target = piles[idx] ^ xor
        if target < piles[idx]:
            return "WIN " + str(idx + 1) + " " + str(piles[idx] - target)
    return "LOSE"
