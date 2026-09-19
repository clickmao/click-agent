"""Conway's Game of Life."""


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = map(int, lines[idx].split())
    grid = []
    for r in range(h):
        row = lines[idx + 1 + r]
        grid.append([c == "#" for c in row[:w]])
    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                            cnt += 1
                if grid[r][c]:
                    nxt[r][c] = cnt == 2 or cnt == 3
                else:
                    nxt[r][c] = cnt == 3
        grid = nxt
    return "\n".join("".join("#" if cell else "." for cell in row) for row in grid)
