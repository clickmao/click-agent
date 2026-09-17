"""Multi-pile Nim: report the winning move with the smallest pile index, or LOSE.

solve(text) is pure: text is the complete stdin, the return value is the
complete stdout (no trailing newline).
"""


def solve(text: str) -> str:
    tokens = text.split()
    if not tokens:
        return ""

    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]

    xor = 0
    for a in piles:
        xor ^= a

    if xor == 0:
        return "LOSE"

    # Winning move: make the total xor zero. For the first pile whose value
    # exceeds (value ^ xor) this is unique; smaller piles cannot be reduced.
    for p, a in enumerate(piles, start=1):
        r = a - (a ^ xor)
        if r > 0:
            return "WIN %d %d" % (p, r)

    return "LOSE"
