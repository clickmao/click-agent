"""Conway's Game of Life: k 代演化。"""


def solve(text: str) -> str:
    lines = text.splitlines()
    if not lines:
        return ''
    h, w, k = (int(x) for x in lines[0].split())
    rows = [line[:w] for line in lines[1:1 + h]]
    grid = [[c == '#' for c in row] for row in rows]
    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx]:
                            cnt += 1
                if grid[y][x]:
                    nxt[y][x] = cnt == 2 or cnt == 3
                else:
                    nxt[y][x] = cnt == 3
        grid = nxt
    return '\n'.join(''.join('#' if c else '.' for c in row) for row in grid)
