"""Nim: m heaps a1..am; remove any positive number from one heap.
Last stone wins. Output 'WIN p r' with smallest heap index p and
amount r removed (at most one winning move per heap), or 'LOSE'.
"""


def solve(text: str) -> str:
    data = text.split()
    if not data:
        return ""
    m = int(data[0])
    heaps = [int(x) for x in data[1:1 + m]]

    x = 0
    for a in heaps:
        x ^= a
    if x == 0:
        return "LOSE"

    for idx in range(m):
        target = heaps[idx] ^ x
        if target < heaps[idx]:
            return "WIN %d %d" % (idx + 1, heaps[idx] - target)
    return "LOSE"
