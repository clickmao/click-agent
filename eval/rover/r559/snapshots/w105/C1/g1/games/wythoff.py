def solve(text: str) -> str:
    a, b = map(int, text.split())

    MAX = 25
    lose = set()
    for s in range(0, 2 * MAX + 1):
        for i in range(0, MAX + 1):
            j = s - i
            if j < 0 or j > MAX:
                continue
            key = (min(i, j), max(i, j))
            if key in lose:
                continue
            if i == 0 and j == 0:
                lose.add(key)
                continue
            can_reach_lose = False
            for ni in range(0, i + 1):
                for nj in range(0, j + 1):
                    if ni == i and nj == j:
                        continue
                    step = (i - ni, j - nj)
                    if step[0] != 0 and step[1] != 0 and step[0] != step[1]:
                        continue
                    if (min(ni, nj), max(ni, nj)) in lose:
                        can_reach_lose = True
                        break
                if can_reach_lose:
                    break
            if not can_reach_lose:
                lose.add(key)

    if (min(a, b), max(a, b)) in lose:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            ni, nj = a - i, b - j
            if (min(ni, nj), max(ni, nj)) in lose:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return 'WIN %d %d' % best
