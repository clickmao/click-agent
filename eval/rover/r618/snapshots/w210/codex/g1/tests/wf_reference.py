import sys

N = 25
win = [[False] * (N + 1) for _ in range(N + 1)]
for x in range(N + 1):
    for y in range(N + 1):
        w = False
        for t in range(1, x + 1):
            if not win[x - t][y]:
                w = True
        for t in range(1, y + 1):
            if not win[x][y - t]:
                w = True
        for t in range(1, min(x, y) + 1):
            if not win[x - t][y - t]:
                w = True
        win[x][y] = w


def expect(a, b):
    if not win[a][b]:
        return "LOSE"
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not ((i > 0 and j == 0) or (i == 0 and j > 0) or (i == j)):
                continue
            if not win[a - i][b - j]:
                return "WIN %d %d" % (i, j)


if __name__ == "__main__":
    for line in sys.stdin:
        parts = line.split()
        if len(parts) < 2:
            continue
        print(expect(int(parts[0]), int(parts[1])))
