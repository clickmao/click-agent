"""Subtraction game: last stone wins. Output minimal winning first move."""


def solve(text: str) -> str:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    n, k = (int(x) for x in lines[0].split())
    moves = sorted(int(x) for x in lines[1].split())

    # win[i] = True if the player to move with i stones has a winning strategy.
    win = [False] * (n + 1)
    first = [None] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                first[i] = s  # moves ascending -> smallest winning take
                break

    if first[n] is None:
        return "LOSE"
    return "WIN %d" % first[n]
