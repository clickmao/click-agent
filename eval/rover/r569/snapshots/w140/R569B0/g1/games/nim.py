"""多堆 Nim: 必胜时给出堆号最小的必胜着法。"""


def solve(text):
    lines = text.split("\n")
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()[:m]]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    for idx in range(m):
        a = piles[idx]
        target = a ^ x
        if target < a:
            return "WIN " + str(idx + 1) + " " + str(a - target)
    return "LOSE"
