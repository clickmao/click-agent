def solve(text: str) -> str:
    data = text.split()
    a = int(data[0])
    b = int(data[1])
    lose = set()
    LIM = 40
    for n in range(LIM + 1):
        x = n * 3 // 2 + n
        y = x + n
        lose.add((x, y))
        lose.add((y, x))

    def is_losing(p: int, q: int) -> bool:
        return (p, q) in lose

    if is_losing(a, b):
        return "LOSE"
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if is_losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    return "WIN %d %d" % best
