"""Wythoff game: decide first-player loss and lexicographically smallest winning move."""


def _is_losing(a: int, b: int) -> bool:
    lo, hi = (a, b) if a <= b else (b, a)
    return (hi - lo) * 5 // 3 == lo


def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])

    if _is_losing(a, b):
        return "LOSE"

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _is_losing(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break
    return "WIN %d %d" % best
