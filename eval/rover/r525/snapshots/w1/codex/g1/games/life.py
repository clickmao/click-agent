"""Conway's Game of Life."""


def solve(text: str) -> str:
    lines = text.split("\n")
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + r]) for r in range(h)]

    def neighbors(r, c):
        cnt = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == "#":
                    cnt += 1
        return cnt

    for _ in range(k):
        nxt = [row[:] for row in grid]
        for r in range(h):
            for c in range(w):
                alive = grid[r][c] == "#"
                n = neighbors(r, c)
                if alive and n in (2, 3):
                    nxt[r][c] = "#"
                elif not alive and n == 3:
                    nxt[r][c] = "#"
                else:
                    nxt[r][c] = "."
        grid = nxt

    return "\n".join("".join(row) for row in grid)
