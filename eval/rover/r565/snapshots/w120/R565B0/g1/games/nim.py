"""Multi-pile Nim: WIN p r / LOSE."""


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    m = int(lines[idx].strip())
    idx += 1
    a = [int(x) for x in lines[idx].split()][:m]
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return "LOSE"
    for i in range(m):
        target = a[i] ^ x
        if target < a[i]:
            return "WIN " + str(i + 1) + " " + str(a[i] - target)
    return "LOSE"
