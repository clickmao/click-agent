def solve(text: str) -> str:
    tokens = text.split()
    pos = 0
    n = int(tokens[pos]); pos += 1
    k = int(tokens[pos]); pos += 1
    moves = []
    for _ in range(k):
        moves.append(int(tokens[pos])); pos += 1
    moves_set = sorted(set(moves))
    # 正常博弈：取走最后一颗者胜 => n==0 是必败态
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in moves_set:
            if s <= x and not win[x - s]:
                win[x] = True
                break
    if not win[n]:
        return 'LOSE'
    best = None
    for s in moves_set:
        if s <= n and not win[n - s]:
            best = s
            break
    return 'WIN ' + str(best)
