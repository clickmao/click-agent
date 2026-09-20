"""Conway's Game of Life: k generations."""


def solve(text: str) -> str:
    lines = text.split('\n')
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + i]) for i in range(h)]
    for _ in range(k):
        nxt = [['.'] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] == '#':
                            cnt += 1
                alive = grid[y][x] == '#'
                if alive and (cnt == 2 or cnt == 3):
                    nxt[y][x] = '#'
                elif not alive and cnt == 3:
                    nxt[y][x] = '#'
        grid = nxt
    return '\n'.join(''.join(row) for row in grid)
