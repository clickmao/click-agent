"""Nim: normal play, take any positive number from one heap."""


def solve(text: str) -> str:
    lines = text.split("\n")
    m = int(lines[0].split()[0])
    heaps = [int(x) for x in lines[1].split()][:m]
    x = 0
    for a in heaps:
        x ^= a
    if x == 0:
        return "LOSE"
    for idx in range(len(heaps)):
        target = heaps[idx] ^ x
        if target < heaps[idx]:
            return "WIN %d %d" % (idx + 1, heaps[idx] - target)
    return "LOSE"
