"""Multi-pile Nim (m <= 4 piles, each <= 15 stones, remove any positive amount).

solve(text) returns "WIN p r" for the winning move with the smallest pile index
p (1-based) and the amount r removed from that pile, or "LOSE" if losing. The
position is losing iff the xor of all piles is 0. For the smallest winning pile,
r = heap - (heap xor total) is the unique winning amount.
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    if not lines:
        return "LOSE"
    head = lines[0].split()
    if not head:
        return "LOSE"
    m = int(head[0])
    heaps = []
    for line in lines[1:]:
        heaps.extend(int(x) for x in line.split())
        if len(heaps) >= m:
            break
    heaps = heaps[:m]

    total = 0
    for h in heaps:
        total ^= h
    if total == 0:
        return "LOSE"
    for idx, h in enumerate(heaps, start=1):
        r = h - (h ^ total)
        if r > 0:
            return "WIN %d %d" % (idx, r)
    return "LOSE"
