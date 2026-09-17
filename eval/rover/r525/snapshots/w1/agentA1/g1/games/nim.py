"""Multi-pile Nim: winning move (smallest pile index, then required count)."""


def solve(text: str) -> str:
    tokens = []
    for line in text.split("\n"):
        tokens.extend(line.split())
    it = iter(tokens)
    m = int(next(it))
    heaps = [int(next(it)) for _ in range(m)]

    xor = 0
    for a in heaps:
        xor ^= a

    if xor == 0:
        return "LOSE"

    # For a winning position each pile with a_i ^ xor < a_i admits exactly
    # one winning reduction; take the smallest such pile index.
    for i, a in enumerate(heaps):
        target = a ^ xor
        if target < a:
            return "WIN %d %d" % (i + 1, a - target)
    return "LOSE"
