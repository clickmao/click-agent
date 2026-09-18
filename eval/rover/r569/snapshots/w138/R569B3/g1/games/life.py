import sys


def _step(grid, h, w):
    out = [['.'] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == '#':
                        n += 1
            if grid[r][c] == '#':
                out[r][c] = '#' if n == 2 or n == 3 else '.'
            else:
                out[r][c] = '#' if n == 3 else '.'
    return out


def solve(text):
    lines = text.split('\n')
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + i][:w]) for i in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(''.join(row) for row in grid)


if __name__ == '__main__':
    sys.stdout.write(solve(sys.stdin.read()))
