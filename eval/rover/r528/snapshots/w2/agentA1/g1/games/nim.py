"""Nim: report the winning move (smallest heap index) or LOSE."""


def solve(text: str) -> str:
    """m heaps; a move takes any positive count from exactly one heap."""
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    piles = [int(v) for v in lines[1].split()[:m]]

    xor_sum = 0
    for a in piles:
        xor_sum ^= a
    if xor_sum == 0:
        return 'LOSE'

    for idx in range(m):  # heap index ascending -> smallest heap wins
        target = piles[idx] ^ xor_sum
        if target < piles[idx]:
            return 'WIN %d %d' % (idx + 1, piles[idx] - target)
    return 'LOSE'  # unreachable for a non-zero xor
