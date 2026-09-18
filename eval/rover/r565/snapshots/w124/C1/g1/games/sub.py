from typing import List


def solve(text: str) -> str:
    data = text.split()
    n = int(data[0])
    k = int(data[1])
    steps: List[int] = [int(x) for x in data[2:2 + k]]
    steps = sorted(set(steps))

    win = [False] * (n + 1)
    move = [None] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                if move[i] is None or s < move[i]:
                    move[i] = s
    if win[n]:
        return "WIN %d" % move[n]
    return "LOSE"
