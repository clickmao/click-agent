"""Conway's Game of Life: H W k then H lines of W chars."""
import sys


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = map(int, lines[idx].split())
    grid = []
    for i in range(h):
        row = lines[idx + 1 + i]
        grid.append([1 if c == "#" else 0 for c in row[:w]])
    for _ in range(k):
        nxt = [[0] * w for _ in range(h)]
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
                if grid[y][x]:
                    nxt[y][x] = 1 if cnt in (2, 3) else 0
                else:
                    nxt[y][x] = 1 if cnt == 3 else 0
        grid = nxt
    return "\n".join("".join("#" if v else "." for v in row) for row in grid)
