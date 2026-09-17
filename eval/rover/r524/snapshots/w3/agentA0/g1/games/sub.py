"""Subtraction game: decide win/lose for the first player and the smallest winning move.

Input text layout (the whole stdin):
    line 1: n k     (1<=n<=80 stones, 1<=k<=12 allowed move counts)
    line 2: k distinct integers s1..sk (1<=si<=12, guaranteed to contain 1)

Play: two players alternate, each removes exactly one of the allowed counts;
whoever takes the last stone wins.

Output:
    first player has a winning strategy -> "WIN m"  (m = smallest winning first move)
    otherwise                            -> "LOSE"
No trailing newline.
"""

__all__ = ["solve"]


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    n, k = (int(x) for x in lines[idx].split())
    idx += 1

    moves = []
    while idx < len(lines) and len(moves) < k:
        moves.extend(int(x) for x in lines[idx].split())
        idx += 1
    moves = sorted(set(moves))

    # win[i] = True iff position with i stones is a win for the player to move.
    # Only reachable moves (si <= i) are considered.
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
