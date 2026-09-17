"""Subtraction game: last player to take wins. Report smallest winning first move."""


def solve(text: str) -> str:
    lines = [ln for ln in text.split("\n") if ln.strip() != ""]
    n, k = map(int, lines[0].split())
    steps = sorted(map(int, lines[1].split()))

    # win[i] = True if player to move with i stones can force a win.
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
