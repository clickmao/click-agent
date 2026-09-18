"""多堆 Nim：输出字典序（先堆号小）最小的必胜着法。"""


def solve(text: str) -> str:
    lines = text.split("\n")
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()[:m]]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    for idx in range(m):
        target = piles[idx] ^ x
        if target < piles[idx]:
            return "WIN " + str(idx + 1) + " " + str(piles[idx] - target)
    return "LOSE"
