def solve(text: str) -> str:
    lines = text.split("\n")
    n, k = (int(x) for x in lines[0].split())
    s = [int(x) for x in lines[1].split()][:k]
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for move in s:
            if move <= i and not win[i - move]:
                win[i] = True
                break
    if not win[n]:
        return "LOSE"
    for move in sorted(s):
        if move <= n and not win[n - move]:
            return "WIN %d" % move
    return "LOSE"
