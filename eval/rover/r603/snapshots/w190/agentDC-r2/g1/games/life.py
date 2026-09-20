"""Conway's Game of Life."""


def solve(text: str) -> str:
    lines = text.splitlines()
    if not lines:
        return ""
    h, w, k = (int(x) for x in lines[0].split()[:3])
    grid = []
    for i in range(h):
        row = lines[1 + i] if 1 + i < len(lines) else ""
        row = row.ljust(w, ".")[:w]
        grid.append([c == "#" for c in row])
    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                            cnt += 1
                if grid[r][c]:
                    nxt[r][c] = cnt in (2, 3)
                else:
                    nxt[r][c] = cnt == 3
        grid = nxt
    return "\n".join("".join("#" if v else "." for v in row) for row in grid)
