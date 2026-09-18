"""多堆 Nim: 每步从某一堆取任意正数颗。"""


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    piles = []
    while idx < len(lines) and len(piles) < m:
        piles.extend(int(x) for x in lines[idx].split())
        idx += 1
    piles = piles[:m]

    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return "LOSE"
    for p in range(1, m + 1):
        a = piles[p - 1]
        target = a ^ xor
        if target < a:
            return "WIN %d %d" % (p, a - target)
    return "LOSE"
