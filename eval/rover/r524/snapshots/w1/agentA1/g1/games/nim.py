"""Game `nim`: multi-pile Nim, winning-move decision.

Input : first line "m" (1<=m<=4 piles); second line m integers a1..am
        (1<=ai<=15 stones per pile).
Output: "WIN p r" when the first player has a winning strategy -- p is the
        smallest pile index (1-based) admitting a winning move and r the number
        of stones removed from it (at most one winning move per pile);
        otherwise "LOSE".

Play: players alternately remove any positive number of stones from a single
pile; the player taking the last stone wins (normal play).
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]

    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return "LOSE"

    for idx, a in enumerate(piles):
        target = a ^ xor          # pile size after the move; target < a
        if target < a:
            return "WIN %d %d" % (idx + 1, a - target)
    return "LOSE"
