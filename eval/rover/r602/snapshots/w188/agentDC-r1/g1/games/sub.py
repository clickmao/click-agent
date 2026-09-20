"""Subtraction game: n stones, allowed moves s1..sk (contains 1).
Take exactly one allowed amount; taking the last stone wins.
Output 'WIN m' with the numerically smallest winning first move,
or 'LOSE' if the first player loses.
"""


def solve(text: str) -> str:
    data = text.split()
    if not data:
        return ""
    n = int(data[0])
    k = int(data[1])
    moves = sorted(int(x) for x in data[2:2 + k])

    # win[i] = True if position with i stones is winning for player to move
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
