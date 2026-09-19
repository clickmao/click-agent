"""康威生命游戏: H 代演化。"""


def solve(text):
    lines = text.split('\n')
    h, w, k = map(int, lines[0].split())
    grid = [[c == '#' for c in lines[1 + i]] for i in range(h)]
    for _ in range(k):
        ng = [[False] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx]:
                            cnt += 1
                alive = grid[y][x]
                ng[y][x] = (cnt == 2 or cnt == 3) if alive else (cnt == 3)
        grid = ng
    return '\n'.join(''.join('#' if c else '.' for c in row) for row in grid)
