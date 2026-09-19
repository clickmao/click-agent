def solve(text: str) -> str:
    lines = text.splitlines()
    n, k = map(int, lines[0].split())
    steps = list(map(int, lines[1].split()))[:k]

    win = [False] * (n + 1)
    for i in range(1, n + 1):
        win[i] = any(s <= i and not win[i - s] for s in steps)

    if not win[n]:
        return "LOSE"

    best = min(s for s in steps if s <= n and not win[n - s])
    return "WIN %d" % best
