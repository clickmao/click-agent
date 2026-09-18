"""多堆 Nim：WIN p r / LOSE。"""


def solve(text: str) -> str:
    lines = text.split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return ""
    m = int(lines[0].split()[0])
    piles = list(map(int, lines[1].split()))[:m] if len(lines) > 1 else []
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return "LOSE"
    for i, p in enumerate(piles):
        target = p ^ x
        if target < p:
            return "WIN %d %d" % (i + 1, p - target)
    return "LOSE"
