"""Conway's Game of Life: evolve the grid k generations, return the resulting grid.

Input text layout (the whole stdin):
    line 1: H W k            (1<=H,W<=20, 0<=k<=20)
    next H lines: strings of length W over {'.', '#'}

Rules: simultaneous update, 8-neighbourhood, everything outside the grid is dead.
Live cell survives iff live-neighbour count is 2 or 3; dead cell becomes alive
iff live-neighbour count is exactly 3.

Output: k-th generation grid, H lines of W chars over {'.', '#'}; no trailing newline.
"""

__all__ = ["solve"]


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    idx += 1

    grid = []
    for _ in range(h):
        # pad/truncate defensively is not needed per spec; take exactly W chars
        row = lines[idx] if idx < len(lines) else ""
        idx += 1
        grid.append([ch == "#" for ch in row[:w]])

    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                n = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx]:
                            n += 1
                if grid[y][x]:
                    nxt[y][x] = n == 2 or n == 3
                else:
                    nxt[y][x] = n == 3
        grid = nxt

    return "\n".join("".join("#" if c else "." for c in row) for row in grid)
