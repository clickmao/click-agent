"""Subtraction game: first player win/lose and minimal winning first move.

stdin format:
  line 1: n k  (1<=n<=80 stones, 1<=k<=12)
  line 2: k distinct allowed removals, contains 1
Output: 'WIN m' (m = smallest winning first removal) or 'LOSE'.
"""



def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = (int(v) for v in lines[0].split())
    moves = sorted(int(v) for v in lines[1].split())[:k]

    # win[i] = True iff position with i stones is a win for player to move
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    # unreachable when win[n] is True
    return 'LOSE'
