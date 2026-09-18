"""Nim: smallest-index winning move for m (<=4) heaps."""


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    heaps = []
    while len(heaps) < m and idx < len(lines):
        heaps.extend(int(t) for t in lines[idx].split())
        idx += 1
    heaps = heaps[:m]

    xor = 0
    for a in heaps:
        xor ^= a
    if xor == 0:
        return "LOSE"

    for p, a in enumerate(heaps, start=1):
        target = a ^ xor
        if target < a:
            return "WIN %d %d" % (p, a - target)
    return "LOSE"
