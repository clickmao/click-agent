import sys


def solve(text: str) -> str:
    sys.setrecursionlimit(10000)
    lines = text.strip().splitlines()
    n, k = map(int, lines[0].split())
    steps = list(map(int, lines[1].split()))
    win = [False] * (n + 1)
    move = [0] * (n + 1)
    for x in range(1, n + 1):
        for s in steps:
            if s <= x and not win[x - s]:
                win[x] = True
                move[x] = s
                break
    if win[n]:
        return "WIN %d" % move[n]
    return "LOSE"
