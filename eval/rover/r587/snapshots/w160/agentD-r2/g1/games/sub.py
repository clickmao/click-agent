def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    n, k = map(int, lines[idx].split())
    idx += 1
    moves = []
    while idx < len(lines) and len(moves) < k:
        moves.extend(int(x) for x in lines[idx].split())
        idx += 1
    moves = sorted(set(moves))

    # win[x] = True 表示轮到面对 x 颗石子者必胜
    win = [False] * (n + 1)
    first = [None] * (n + 1)
    for x in range(1, n + 1):
        for s in moves:
            if s <= x and not win[x - s]:
                win[x] = True
                first[x] = s
                break

    if win[n]:
        return 'WIN %d' % first[n]
    return 'LOSE'
