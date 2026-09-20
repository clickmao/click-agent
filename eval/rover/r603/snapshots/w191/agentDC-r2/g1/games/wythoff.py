import sys


def solve(text: str) -> str:
    tokens = text.split()
    it = iter(tokens)
    a = int(next(it))
    b = int(next(it))
    losing = set()
    limit = max(a, b) + 1
    i = 0
    while True:
        p = (i * (1 + 5 ** 0.5)) / 2.0
        x = int(p)
        y = x + i
        if x > limit or y > limit:
            break
        losing.add((x, y))
        losing.add((y, x))
        i += 1
        if i > 1000:
            break
    if (a, b) in losing:
        return "LOSE"
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if i > a or j > b:
                continue
            if (a - i, b - j) in losing:
                return "WIN " + str(i) + " " + str(j)
    return "LOSE"


if __name__ == "__main__":
    sys.stdout.write(solve(sys.stdin.read()))
