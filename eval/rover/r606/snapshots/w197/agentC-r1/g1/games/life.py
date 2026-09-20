"""Conway's Game of Life: evolve HxW grid k generations.

stdin format:
  line 1: H W k   (1<=H,W<=20, 0<=k<=20)
  next H lines: W chars each, '.' dead / '#' alive
Output: grid after k generations, H lines of W chars.
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    first = lines[0].split()
    h = int(first[0])
    w = int(first[1])
    k = int(first[2])
    grid = []
    for i in range(h):
        row = lines[1 + i]
        grid.append([c == '#' for c in row[:w]])

    def step(g):
        ng = [[False] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                n = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        ny = y + dy
                        nx = x + dx
                        if 0 <= ny < h and 0 <= nx < w and g[ny][nx]:
                            n += 1
                if g[y][x]:
                    ng[y][x] = n in (2, 3)
                else:
                    ng[y][x] = n == 3
        return ng

    for _ in range(k):
        grid = step(grid)

    out = []
    for y in range(h):
        out.append(''.join('#' if grid[y][x] else '.' for x in range(w)))
    return '\n'.join(out)
