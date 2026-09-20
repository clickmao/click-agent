"""Subtraction game: decide WIN m / LOSE for the first player."""


def _split_lines(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    while lines and lines[0].strip() == "":
        lines.pop(0)
    while lines and lines[-1].strip() == "":
        lines.pop()
    return lines


def solve(text: str) -> str:
    lines = _split_lines(text)
    n, k = (int(x) for x in lines[0].split())
    moves = sorted(int(x) for x in lines[1].split())

    win = [False] * (n + 1)
    for total in range(1, n + 1):
        for s in moves:
            if s <= total and not win[total - s]:
                win[total] = True
                break

    if not win[n]:
        return "LOSE"

    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN %d" % s

    return "LOSE"
