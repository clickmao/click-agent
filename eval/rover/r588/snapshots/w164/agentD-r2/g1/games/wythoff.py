"""Wythoff game: defeat positions and lexicographically smallest winning move."""


def solve(text: str) -> str:
    lines = text.split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    a, b = map(int, lines[0].split())

    n = max(a, b)
    cold = [[False] * (n + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        for j in range(n + 1):
            ok = False
            for t in range(1, i + 1):
                if cold[i - t][j]:
                    ok = True
                    break
            if not ok:
                for t in range(1, j + 1):
                    if cold[i][j - t]:
                        ok = True
                        break
            if not ok:
                for t in range(1, min(i, j) + 1):
                    if cold[i - t][j - t]:
                        ok = True
                        break
            cold[i][j] = not ok

    if cold[a][b]:
        return "LOSE"
    best_i = best_j = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not ((i > 0 and j == 0) or (i == 0 and j > 0) or (i == j)):
                continue
            if cold[a - i][b - j]:
                best_i, best_j = i, j
                break
        if best_i is not None:
            break
    return "WIN " + str(best_i) + " " + str(best_j)
