import sys


def solve(text):
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    if not lines:
        return ''
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + i]) for i in range(h)]
    for _ in range(k):
        ng = [['.'] * w for _ in range(h)]
        for i in range(h):
            for j in range(w):
                cnt = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < h and 0 <= nj < w and grid[ni][nj] == '#':
                            cnt += 1
                alive = grid[i][j] == '#'
                if alive and cnt in (2, 3):
                    ng[i][j] = '#'
                elif not alive and cnt == 3:
                    ng[i][j] = '#'
        grid = ng
    out = ['\n'.join(''.join(row) for row in grid) for _ in range(1)][0]
    return out


if __name__ == '__main__':
    sys.stdout.write(solve(sys.stdin.read()))
