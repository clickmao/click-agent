"""Wythoff game: LOSE for cold positions, else lexicographically smallest WIN i j."""

LIMIT = 26


def _cold_table(limit):
    cold = [[False] * (limit + 1) for _ in range(limit + 1)]
    for a in range(limit + 1):
        for b in range(a, limit + 1):
            if a == 0 and b == 0:
                cold[a][b] = cold[b][a] = True
                continue
            is_cold = True
            # take from a single pile: (a - i, b) or (a, b - j)
            for i in range(1, a + 1):
                if cold[a - i][b]:
                    is_cold = False
                    break
            if is_cold:
                for j in range(1, b + 1):
                    if cold[a][b - j]:
                        is_cold = False
                        break
            if is_cold:
                # take the same amount t from both piles
                for t in range(1, min(a, b) + 1):
                    if cold[a - t][b - t]:
                        is_cold = False
                        break
            cold[a][b] = cold[b][a] = is_cold
    return cold


_COLD = _cold_table(LIMIT)


def solve(text):
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    if _COLD[a][b]:
        return "LOSE"
    # candidate moves, note: taking i from pile1 reduces its size by i
    candidates = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if _COLD[na][nb]:
                candidates.append((i, j))
    candidates.sort()
    i, j = candidates[0]
    return "WIN %d %d" % (i, j)
