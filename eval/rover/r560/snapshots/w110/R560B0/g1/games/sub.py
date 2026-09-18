def solve(text):
    lines = [ln for ln in text.split("\n") if ln.strip() != ""]
    n, k = (int(x) for x in lines[0].split())
    moves = sorted(int(x) for x in lines[1].split())
    losing = [False] * (n + 1)
    losing[0] = True
    for i in range(1, n + 1):
        losing[i] = all(losing[i - s] for s in moves if s <= i)
    if losing[n]:
        return "LOSE"
    for s in moves:
        if s <= n and losing[n - s]:
            return "WIN %d" % s
    return "LOSE"
