"""Subtraction game: first-player win/lose and smallest winning move."""


def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n') if ln.strip() != '']
    n, k = (int(x) for x in lines[0].split())
    steps = sorted(int(x) for x in lines[1].split())
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                break
    if win[n]:
        for s in steps:
            if s <= n and not win[n - s]:
                return "WIN %d" % s
    return "LOSE"
