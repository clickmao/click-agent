"""Subtraction game: determine win/lose and the smallest winning first move."""


def solve(text: str) -> str:
    lines = text.splitlines()
    n, k = (int(t) for t in lines[0].split())
    moves = [int(t) for t in lines[1].split()]
    win = [False] * (n + 1)
    first = [None] * (n + 1)
    for x in range(1, n + 1):
        for s in sorted(moves):
            if s <= x and not win[x - s]:
                win[x] = True
                first[x] = s
                break
    if win[n]:
        return "WIN %d" % first[n]
    return "LOSE"
