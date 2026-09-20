"""多堆 Nim 必胜手。"""


def solve(text: str) -> str:
    lines = text.splitlines()
    i = 0
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    m = int(lines[i].split()[0])
    i += 1
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    piles = [int(x) for x in lines[i].split()][:m]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"

    for idx in range(m):
        target = piles[idx] ^ x
        if target < piles[idx]:
            return "WIN %d %d" % (idx + 1, piles[idx] - target)
    return "LOSE"
