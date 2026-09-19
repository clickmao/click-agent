LIM = 30


def _cold():
    cold = set()
    for a in range(LIM + 1):
        for b in range(LIM + 1):
            if a == 0 and b == 0:
                continue
            is_cold = True
            for i in range(a + 1):
                if not is_cold:
                    break
                for j in range(b + 1):
                    if i == 0 and j == 0:
                        continue
                    if i > a or j > b:
                        continue
                    if (a - i, b - j) in cold:
                        is_cold = False
                        break
            for t in range(1, min(a, b) + 1):
                if (a - t, b - t) in cold:
                    is_cold = False
                    break
            if is_cold:
                cold.add((a, b))
    return cold


COLD = _cold()


def solve(text):
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])

    if (a, b) in COLD:
        return "LOSE"

    moves = []
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0 or j == 0 or i == j):
                if (a - i, b - j) in COLD:
                    moves.append((i, j))
    moves.sort()
    i, j = moves[0]
    return "WIN " + str(i) + " " + str(j)
