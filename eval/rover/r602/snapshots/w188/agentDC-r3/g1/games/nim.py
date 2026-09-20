"""Nim: find the winning move (smallest pile index, stones to take)."""


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
    m = int(lines[0].split()[0])
    heaps = [int(x) for x in lines[1].split()][:m]

    xor = 0
    for a in heaps:
        xor ^= a

    if xor == 0:
        return "LOSE"

    for idx, a in enumerate(heaps):
        target = a ^ xor
        if target < a:
            return "WIN %d %d" % (idx + 1, a - target)

    return "LOSE"
