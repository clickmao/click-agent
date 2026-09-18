def solve(text: str) -> str:
    data = text.split()
    n, k = int(data[0]), int(data[1])
    moves = [int(x) for x in data[2:2 + k]]

    win = [False] * (n + 1)
    choice = [0] * (n + 1)
    for i in range(1, n + 1):
        for s in sorted(moves):
            if s <= i and not win[i - s]:
                win[i] = True
                choice[i] = s
                break

    if not win[n]:
        return 'LOSE'
    return 'WIN %d' % choice[n]
