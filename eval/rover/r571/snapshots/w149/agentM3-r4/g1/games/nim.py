"""Multi-pile Nim: smallest-index winning heap and the amount to take."""


def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n') if ln.strip() != '']
    m = int(lines[0].split()[0])
    heaps = [int(x) for x in lines[1].split()][:m]
    x = 0
    for a in heaps:
        x ^= a
    if x == 0:
        return "LOSE"
    for idx, a in enumerate(heaps):
        target = a ^ x
        if target < a:
            return "WIN %d %d" % (idx + 1, a - target)
    return "LOSE"
