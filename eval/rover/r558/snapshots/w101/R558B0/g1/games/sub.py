"""Subtraction game: first player win/lose and smallest winning first move.

Input text format:
  line 1: n k  (n stones, k allowed move sizes)
  line 2: k distinct integers s1..sk (each >=1), which include 1
Output:
  'WIN m' with m the smallest winning first move, or 'LOSE'.
Last stone taken wins. Moves remove exactly one allowed amount.
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    n, k = map(int, lines[0].split())
    moves = sorted(int(x) for x in lines[1].split())[:k]

    win = [False] * (n + 1)
    for stones in range(1, n + 1):
        for s in moves:
            if s > stones:
                break
            if not win[stones - s]:
                win[stones] = True
                break

    if not win[n]:
        return "LOSE"
    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN " + str(s)
    return "LOSE"
