def solve(text: str) -> str:
    lines = text.split(chr(10))
    first = lines[0].split()
    n, k = int(first[0]), int(first[1])
    moves = [int(x) for x in lines[1].split()]
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in sorted(moves):
        if s <= n and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
