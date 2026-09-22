"""Subtraction game: report WIN with smallest winning first move, else LOSE."""


def solve(text: str) -> str:
    lines = text.split("\n")
    n, k = (int(x) for x in lines[0].split())
    steps = sorted(int(x) for x in lines[1].split()[:k])
    losing = [False] * (n + 1)
    losing[0] = True
    for i in range(1, n + 1):
        losing[i] = all(not losing[i - s] for s in steps if s <= i)
    if losing[n]:
        return "LOSE"
    for s in steps:
        if s <= n and losing[n - s]:
            return "WIN %d" % s
    return "LOSE"
