def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    n, k = map(int, lines[idx].split())
    idx += 1
    moves = list(map(int, lines[idx].split()))
    lose = [False] * (n + 1)
    lose[0] = True
    for x in range(1, n + 1):
        lose[x] = all(not lose[x - s] for s in moves if s <= x)
    if lose[n]:
        return "LOSE"
    for s in sorted(moves):
        if s <= n and lose[n - s]:
            return "WIN %d" % s
