# Wythoff game: report losing position or lexicographically smallest winning move.

def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])

    def is_losing(x, y):
        lo = min(x, y)
        hi = max(x, y)
        r = int((lo * 5) ** 0.5)
        for t in range(max(0, r - 2), r + 3):
            if int(t * (1 + 5 ** 0.5) / 2) == lo and lo + t == hi:
                return True
        return False

    if is_losing(a, b):
        return 'LOSE'
    moves = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0 or j == 0 or i == j) and i <= a and j <= b:
                if is_losing(a - i, b - j):
                    moves.append((i, j))
    i, j = min(moves)
    return 'WIN ' + str(i) + ' ' + str(j)
