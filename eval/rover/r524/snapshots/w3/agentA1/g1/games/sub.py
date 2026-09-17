"""Subtraction game (take-away): decide winner and smallest winning first move.

Input format:
    n k             (1 <= n <= 80 stones ; 1 <= k <= 12)
    k distinct ints s1..sk  (1 <= si <= 12, one of them is guaranteed to be 1)

Players alternately remove exactly one of the allowed amounts; whoever takes
the last stone wins.  Output for a first-player win:
    WIN m           where m is the smallest allowed move that wins
Otherwise:
    LOSE
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    if not lines:
        return ''
    n, k = (int(x) for x in lines[0].split())
    moves = sorted(int(x) for x in lines[1].split())[:k]

    # win[i] == True iff the player to move with i stones can force a win.
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        # i is winning iff some allowed move leads to a losing position.
        for s in moves:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return 'LOSE'
    # Smallest first move that leads to a losing position for the opponent.
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN {}'.format(s)
    return 'LOSE'
