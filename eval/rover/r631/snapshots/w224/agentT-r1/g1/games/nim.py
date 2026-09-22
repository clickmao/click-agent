"""Multi-heap Nim: smallest heap index among winning moves, with amount."""


def solve(text: str) -> str:
    lines = [ln for ln in text.split("\n") if ln.strip() != ""]
    if not lines:
        return ""
    m = int(lines[0].split()[0])
    heaps = [int(x) for x in lines[1].split()][:m]
    x = 0
    for v in heaps:
        x ^= v
    if x == 0:
        return "LOSE"
    best = None
    for idx, v in enumerate(heaps):
        target = v ^ x
        if target < v:
            best = (idx + 1, v - target)
            break
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
