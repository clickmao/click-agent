def solve(text: str) -> str:
    a, b = map(int, text.split())
    los = set()
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            win = (i - j, j) in los if False else False
            for k in range(1, min(i, j) + 1):
                if (i - k, j - k) in los:
                    win = True
                    break
            if not win:
                for k in range(1, i + 1):
                    if (i - k, j) in los:
                        win = True
                        break
            if not win:
                for k in range(1, j + 1):
                    if (i, j - k) in los:
                        win = True
                        break
            if not win:
                los.add((i, j))
    if (a, b) in los:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i, j) not in los:
                continue
            if 0 < i and 0 < j and i != j:
                continue
            if best is None:
                best = (i, j)
    return 'WIN %d %d' % best
