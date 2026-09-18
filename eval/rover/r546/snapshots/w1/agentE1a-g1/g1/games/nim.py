"""多堆 Nim 必胜手。"""


def solve(text: str) -> str:
    lines = text.split()
    m = int(lines[0])
    piles = [int(x) for x in lines[1:1 + m]]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return "LOSE"
    for idx in range(m):
        target = piles[idx] ^ x
        if target < piles[idx]:
            return "WIN " + str(idx + 1) + " " + str(piles[idx] - target)
    return "LOSE"
