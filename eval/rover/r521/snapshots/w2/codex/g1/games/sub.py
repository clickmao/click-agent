def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    n, k = map(int, lines[idx].split())
    idx += 1
    moves = sorted(set(map(int, lines[idx].split())))

    # win[i]: True if the player to move with i stones can win
    win = [False] * (n + 1)
    best = [0] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                best[i] = s
                break

    if not win[n]:
        return "LOSE"
    return "WIN %d" % best[n]
